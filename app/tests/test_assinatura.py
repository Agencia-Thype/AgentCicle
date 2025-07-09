"""
Testes unitários para as funcionalidades de trial e assinatura.

Estes testes verificam:
1. Usuário novo: trial ativo
2. Usuário com mais de 7 dias: acesso bloqueado se não assinou
3. Usuário que assina no meio do trial: tudo liberado
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import sys
import os

# Adicionar caminho do projeto ao PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.assinatura_service import verificar_status_usuario, ativar_assinatura, cancelar_assinatura


class TestAssinatura(unittest.TestCase):
    def setUp(self):
        """Configurar objetos mock para os testes"""
        self.db_mock = MagicMock()
        self.user_id = 1
        
        # Simular data atual para testes
        self.current_time_patcher = patch('app.services.assinatura_service.datetime')
        self.mock_datetime = self.current_time_patcher.start()
        self.mock_datetime.now.return_value = datetime(2025, 6, 24, 12, 0, 0)  # Fixar data atual
        
    def tearDown(self):
        """Limpar os patches após cada teste"""
        self.current_time_patcher.stop()
    
    def test_usuario_novo_trial_ativo(self):
        """Teste 1: Usuário novo deve ter trial ativo"""
        # Configurar mock do usuário novo
        usuario_mock = MagicMock()
        usuario_mock.id = self.user_id
        usuario_mock.data_criacao_conta = None  # Usuário novo sem data de criação
        usuario_mock.data_fim_trial = None
        usuario_mock.assinatura_ativa = 0
        
        # Configurar query que retorna o usuário mock
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=usuario_mock)
        filter_mock.filter.return_value = first_mock
        query_mock.filter.return_value = filter_mock
        self.db_mock.query.return_value = query_mock
        
        # Executar verificação de status
        status = verificar_status_usuario(self.db_mock, self.user_id)
        
        # Verificar se o trial foi inicializado
        self.assertEqual(usuario_mock.data_criacao_conta, self.mock_datetime.now())
        self.assertEqual(usuario_mock.data_fim_trial, self.mock_datetime.now() + timedelta(days=7))
        
        # Verificar status retornado
        self.assertTrue(status['trialAtivo'])
        self.assertFalse(status['assinaturaAtiva'])
        self.assertEqual(status['diasRestantesTrial'], 7)
        self.assertTrue(status['podeUsarRecursosBasicos'])
        self.assertFalse(status['podeUsarPremium'])
        self.assertTrue(status['podePontuar'])
        
    def test_usuario_com_8_dias_trial_expirado(self):
        """Teste 2: Usuário com 8 dias deve ter trial expirado"""
        # Configurar mock do usuário com trial expirado
        usuario_mock = MagicMock()
        usuario_mock.id = self.user_id
        
        # Definir data de criação como 8 dias atrás
        data_criacao = self.mock_datetime.now() - timedelta(days=8)
        data_fim_trial = data_criacao + timedelta(days=7)  # 1 dia atrás
        
        usuario_mock.data_criacao_conta = data_criacao
        usuario_mock.data_fim_trial = data_fim_trial
        usuario_mock.assinatura_ativa = 0
        
        # Configurar query que retorna o usuário mock
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=usuario_mock)
        filter_mock.filter.return_value = first_mock
        query_mock.filter.return_value = filter_mock
        self.db_mock.query.return_value = query_mock
        
        # Executar verificação de status
        status = verificar_status_usuario(self.db_mock, self.user_id)
        
        # Verificar status retornado
        self.assertFalse(status['trialAtivo'])
        self.assertFalse(status['assinaturaAtiva'])
        self.assertEqual(status['diasRestantesTrial'], 0)
        self.assertFalse(status['podeUsarRecursosBasicos'])
        self.assertFalse(status['podeUsarPremium'])
        self.assertFalse(status['podePontuar'])
        
    def test_usuario_assinou_durante_trial(self):
        """Teste 3: Usuário que assinou durante o período de trial"""
        # Configurar mock do usuário com trial ativo e assinatura ativa
        usuario_mock = MagicMock()
        usuario_mock.id = self.user_id
        
        # Definir data de criação como 3 dias atrás (trial ainda ativo)
        data_criacao = self.mock_datetime.now() - timedelta(days=3)
        data_fim_trial = data_criacao + timedelta(days=7)  # 4 dias restantes
        
        usuario_mock.data_criacao_conta = data_criacao
        usuario_mock.data_fim_trial = data_fim_trial
        usuario_mock.assinatura_ativa = 1  # Assinatura ativa
        usuario_mock.data_inicio_assinatura = self.mock_datetime.now() - timedelta(days=1)
        usuario_mock.data_fim_assinatura = self.mock_datetime.now() + timedelta(days=30)
        
        # Configurar query que retorna o usuário mock
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=usuario_mock)
        filter_mock.filter.return_value = first_mock
        query_mock.filter.return_value = filter_mock
        self.db_mock.query.return_value = query_mock
        
        # Executar verificação de status
        status = verificar_status_usuario(self.db_mock, self.user_id)
        
        # Verificar status retornado
        self.assertTrue(status['trialAtivo'])  # Trial ainda está ativo
        self.assertTrue(status['assinaturaAtiva'])  # Assinatura também está ativa
        self.assertEqual(status['diasRestantesTrial'], 4)
        self.assertTrue(status['podeUsarRecursosBasicos'])
        self.assertTrue(status['podeUsarPremium'])  # Acesso a recursos premium liberado
        self.assertTrue(status['podePontuar'])
        
    def test_ativar_assinatura(self):
        """Teste adicional: Ativar assinatura"""
        usuario_mock = MagicMock()
        usuario_mock.id = self.user_id
        
        # Configurar query que retorna o usuário mock
        query_mock = MagicMock()
        filter_mock = MagicMock()
        first_mock = MagicMock(return_value=usuario_mock)
        filter_mock.filter.return_value = first_mock
        query_mock.filter.return_value = filter_mock
        self.db_mock.query.return_value = query_mock
        
        # Mock para a função verificar_status_usuario que é chamada dentro de ativar_assinatura
        with patch('app.services.assinatura_service.verificar_status_usuario') as mock_verificar:
            mock_verificar.return_value = {
                'trialAtivo': False,
                'assinaturaAtiva': True,
                'diasRestantesTrial': 0,
                'podeUsarRecursosBasicos': True,
                'podeUsarPremium': True,
                'podePontuar': True
            }
            
            # Executar função para ativar assinatura
            resultado = ativar_assinatura(self.db_mock, self.user_id, duracao_meses=3)
            
            # Verificar se a assinatura foi ativada corretamente
            self.assertEqual(usuario_mock.assinatura_ativa, 1)
            self.assertEqual(usuario_mock.data_inicio_assinatura, self.mock_datetime.now())
            self.assertEqual(usuario_mock.data_fim_assinatura, self.mock_datetime.now() + timedelta(days=90))
            self.db_mock.commit.assert_called_once()
            
            # Verificar se foi retornado o status atualizado
            self.assertEqual(resultado, mock_verificar.return_value)


if __name__ == '__main__':
    unittest.main()
