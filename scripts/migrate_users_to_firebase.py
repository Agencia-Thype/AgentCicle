"""
Migração one-time dos usuários existentes (bcrypt/senha_hash) para o Firebase
Authentication, preservando a senha original via import de hash bcrypt.

Rode isso primeiro contra uma cópia/dump do banco, nunca direto em produção.
Reexecutável com segurança: só processa usuários com firebase_uid ainda nulo.

Uso:
    python scripts/migrate_users_to_firebase.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from firebase_admin import auth as firebase_auth

from app.db.database import SessionLocal
from app.models.sqlalchemy_models import Usuario
from app.services.firebase_admin_service import get_firebase_app

LOTE = 1000


def montar_registro_import(usuario: Usuario) -> firebase_auth.ImportUserRecord:
    return firebase_auth.ImportUserRecord(
        uid=str(usuario.id),
        email=usuario.email,
        display_name=usuario.nome,
        email_verified=bool(usuario.verificado),
        password_hash=usuario.senha_hash.encode("utf-8") if usuario.senha_hash else None,
    )


def migrar():
    get_firebase_app()
    db = SessionLocal()
    try:
        usuarios = (
            db.query(Usuario)
            .filter(Usuario.firebase_uid.is_(None))
            .filter(Usuario.senha_hash.isnot(None))
            .all()
        )

        if not usuarios:
            print("ℹ️ Nenhum usuário pendente de migração.")
            return

        print(f"Migrando {len(usuarios)} usuários em lotes de {LOTE}...")

        for inicio in range(0, len(usuarios), LOTE):
            lote = usuarios[inicio:inicio + LOTE]
            registros = [montar_registro_import(u) for u in lote]

            resultado = firebase_auth.import_users(
                registros,
                hash_alg=firebase_auth.UserImportHash.bcrypt(),
            )

            print(f"Lote {inicio // LOTE + 1}: {resultado.success_count} ok, {resultado.failure_count} falhas")
            for erro in resultado.errors:
                usuario_com_erro = lote[erro.index]
                print(f"  ❌ {usuario_com_erro.email}: {erro.reason}")

            indices_com_erro = {erro.index for erro in resultado.errors}
            for i, usuario in enumerate(lote):
                if i in indices_com_erro:
                    continue
                usuario.firebase_uid = str(usuario.id)
            db.commit()

        print("✅ Migração concluída.")
    finally:
        db.close()


if __name__ == "__main__":
    migrar()
