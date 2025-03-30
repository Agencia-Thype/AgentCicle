# verificar_usuarios.py
from app.db.database import SessionLocal
from app.models.sqlalchemy_models import Usuario


db = SessionLocal()
usuarios = db.query(Usuario).all()
print("Usuárias cadastradas no banco:\n")
for u in usuarios:
    print(f"• {u.nome} - {u.email}")
