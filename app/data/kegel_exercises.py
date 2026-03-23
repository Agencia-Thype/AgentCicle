from app.models.kegel_models import ExercicioKegel, SerieKegel, FaseKegel, NivelKegel

# Dados dos exercícios de Kegel conforme especificação
KEGEL_EXERCISES = {
    NivelKegel.INICIANTE: [
        ExercicioKegel(
            id="kegel_ini_ex1",
            nome="Exercício 1: Resistência + Agilidade",
            nivel=NivelKegel.INICIANTE,
            objetivo="resistência + agilidade",
            series=3,
            descanso_segundos=30,
            instrucoes=[
                SerieKegel(
                    repeticoes=5,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=4, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=4, instrucao="Relaxe completamente")
                    ]
                ),
                SerieKegel(
                    repeticoes=12,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1.5, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1.5, instrucao="Solte")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_ini_ex2",
            nome="Exercício 2: Resistência + Hipertrofia",
            nivel=NivelKegel.INICIANTE,
            objetivo="resistência + hipertrofia",
            series=3,
            descanso_segundos=30,
            instrucoes=[
                SerieKegel(
                    repeticoes=8,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=3, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="contracao_forte", duracao_segundos=1, instrucao="Contraia mais forte (uma piscada a mais)"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=4, instrucao="Relaxe")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_ini_ex3",
            nome="Exercício 3: Potência + Agilidade",
            nivel=NivelKegel.INICIANTE,
            objetivo="potência e agilidade",
            series=3,
            descanso_segundos=30,
            instrucoes=[
                SerieKegel(
                    repeticoes=20,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1.5, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1.5, instrucao="Solte")
                    ]
                )
            ]
        )
    ],
    NivelKegel.INTERMEDIARIO: [
        ExercicioKegel(
            id="kegel_int_ex1",
            nome="Exercício 1: Resistência + Agilidade",
            nivel=NivelKegel.INTERMEDIARIO,
            objetivo="resistência + agilidade",
            series=3,
            descanso_segundos=45,
            instrucoes=[
                SerieKegel(
                    repeticoes=6,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=6, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=6, instrucao="Relaxe completamente")
                    ]
                ),
                SerieKegel(
                    repeticoes=15,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1, instrucao="Solte")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_int_ex2",
            nome="Exercício 2: Resistência + Hipertrofia",
            nivel=NivelKegel.INTERMEDIARIO,
            objetivo="resistência + hipertrofia",
            series=3,
            descanso_segundos=45,
            instrucoes=[
                SerieKegel(
                    repeticoes=8,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=5, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="contracao_forte", duracao_segundos=2, instrucao="Contraia mais forte mais forte (duas piscadas a mais)"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=7, instrucao="Relaxe")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_int_ex3",
            nome="Exercício 3: Potência + Agilidade",
            nivel=NivelKegel.INTERMEDIARIO,
            objetivo="potência e agilidade",
            series=3,
            descanso_segundos=45,
            instrucoes=[
                SerieKegel(
                    repeticoes=30,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1, instrucao="Solte")
                    ]
                )
            ]
        )
    ],
    NivelKegel.AVANCADO: [
        ExercicioKegel(
            id="kegel_avan_ex1",
            nome="Exercício 1: Resistência + Agilidade",
            nivel=NivelKegel.AVANCADO,
            objetivo="resistência + agilidade",
            series=3,
            descanso_segundos=60,
            instrucoes=[
                SerieKegel(
                    repeticoes=6,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=8, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=8, instrucao="Relaxe completamente")
                    ]
                ),
                SerieKegel(
                    repeticoes=20,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1, instrucao="Solte")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_avan_ex2",
            nome="Exercício 2: Resistência + Hipertrofia",
            nivel=NivelKegel.AVANCADO,
            objetivo="resistência + hipertrofia",
            series=3,
            descanso_segundos=60,
            instrucoes=[
                SerieKegel(
                    repeticoes=8,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=7, instrucao="Contraia e mantenha"),
                        FaseKegel(tipo="contracao_forte", duracao_segundos=2, instrucao="Contraia mais forte mais forte (duas piscadas a mais)"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=9, instrucao="Relaxe")
                    ]
                )
            ]
        ),
        ExercicioKegel(
            id="kegel_avan_ex3",
            nome="Exercício 3: Potência + Agilidade",
            nivel=NivelKegel.AVANCADO,
            objetivo="potência e agilidade",
            series=3,
            descanso_segundos=60,
            instrucoes=[
                SerieKegel(
                    repeticoes=50,
                    fases=[
                        FaseKegel(tipo="contracao", duracao_segundos=1, instrucao="Contraia"),
                        FaseKegel(tipo="relaxamento", duracao_segundos=1, instrucao="Solte")
                    ]
                )
            ]
        )
    ]
}

def get_exercicios_por_nivel(nivel: NivelKegel) -> list:
    """Retorna os exercícios de Kegel para um nível específico"""
    return KEGEL_EXERCISES.get(nivel, [])

def get_all_exercicios() -> dict:
    """Retorna todos os exercícios de Kegel organizados por nível"""
    return KEGEL_EXERCISES
