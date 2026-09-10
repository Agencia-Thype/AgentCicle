"""Datas no fuso do app."""

from datetime import date, datetime, timedelta, timezone

# O app é usado no Brasil e envia datas locais do aparelho, mas o servidor roda
# em UTC: com date.today() o "hoje" do servidor virava o dia seguinte a partir
# das 21h. Brasília não tem horário de verão desde 2019, então offset fixo basta.
FUSO_BRASILIA = timezone(timedelta(hours=-3))


def hoje_brasilia() -> date:
    return datetime.now(FUSO_BRASILIA).date()
