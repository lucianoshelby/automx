from flask import Flask, render_template, request, jsonify, session
import sys
import os
sys.path.append('C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from automacoes.pecas import sincronizar_pecas
from automacoes.cos.coletar_dados_cos import filtrar_dados_saw, obter_os_correspondentes, coletar_dados_os, consultar_id_tecnico_cos
from automacoes.cos.login_cos import carregar_sessao
from multiprocessing import Process, Lock, Queue
from flask_socketio import SocketIO, emit
from flask_session import Session
import threading
import time
import requests
import json
from urllib.parse import quote
from datetime import datetime
from automacoes.cos.auto_cos import processar_submissao_requisicao_para_fila, preparar_dados_para_formulario_requisicao
from automacoes.cos.users_cos import listar_nomes_usuarios, deletar_usuario, recuperar_login, cadastrar_login
from login_gspn.cookies_manager import validar_e_salvar_cookies, verificar_e_limpar_cookies_salvos
import logging
from automacoes.gerar_e_fechar_os import gerenciar_os_gspn_sequencial
from flask_cors import CORS



app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, cors_allowed_origins="*", manage_session=False)
os_em_processamento = set()
lock = Lock()
COOKIES_TEMP_PATH = "cookies_temp.json"
progress_queue = Queue()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
CORS(
    app,
    origins=["http://localhost:5173"],  # Permite APENAS a origem do seu dev server Vite
    methods=["GET", "POST", "OPTIONS"], # Métodos permitidos explicitamente
    allow_headers=["Content-Type"],    # Headers permitidos explicitamente
    supports_credentials=True          # Se você usa cookies/sessões
)

"""@socketio.on('connect')
def handle_connect():
    session['sid'] = request.sid
    logging.info(f"Cliente conectado: {request.sid}")
    logging.info(f"Sessão após conectar: {dict(session)}")
    session.modified = True"""

@app.route('/logins_validos', methods=['GET', 'OPTIONS'])
def handle_listar_logins_validos():
    """
    Rota para verificar todos os cookies salvos, limpar os inválidos
    e retornar uma lista dos IDs de usuário (logins) que permanecem válidos.
    """
    #logging.info("Recebida requisição GET em /logins_validos")

    # Verifica se a função essencial foi importada corretamente
    if verificar_e_limpar_cookies_salvos is None:
         logging.error("Função 'verificar_e_limpar_cookies_salvos' não está disponível.")
         return jsonify({"success": False, "message": "Erro interno no servidor (dependência faltando)."}), 500

    try:
        # Chama a função que faz a verificação, limpeza e retorna a lista de IDs válidos
        lista_ids_validos = verificar_e_limpar_cookies_salvos()

        #logging.info(f"Verificação concluída. Logins válidos encontrados: {lista_ids_validos}")
        # Retorna a lista de IDs válidos em um JSON
        return jsonify({"success": True, "valid_logins": lista_ids_validos}), 200

    except Exception as e:
        # Captura qualquer erro inesperado dentro de verificar_e_limpar_cookies_salvos
        logging.error(f"Erro inesperado durante a execução de verificar_e_limpar_cookies_salvos: {e}", exc_info=True)
        return jsonify({"success": False, "message": "Erro interno no servidor durante a verificação."}), 500

@app.route('/receber_cookies', methods=['POST'])
def handle_receber_cookies():
    """
    Rota para receber uma lista de cookies via POST JSON,
    validá-los e salvá-los.
    Retorna um JSON indicando sucesso ou falha da validação/salvamento.
    """
    #logging.info("Recebida requisição POST em /receber_cookies")

    # Verifica se a função essencial foi importada corretamente
    if validar_e_salvar_cookies is None:
         logging.error("Função 'validar_e_salvar_cookies' não está disponível.")
         return jsonify({"success": False, "message": "Erro interno no servidor (dependência faltando)."}), 500

    # 1. Obter os dados JSON da requisição
    if not request.is_json:
        logging.warning("Requisição recebida sem Content-Type application/json")
        return jsonify({"success": False, "message": "Erro: Content-Type deve ser application/json."}), 415 # Unsupported Media Type

    try:
        lista_cookies_recebida = request.get_json()
    except Exception as e:
        logging.error(f"Erro ao fazer parse do JSON da requisição: {e}")
        return jsonify({"success": False, "message": "Erro: JSON inválido na requisição."}), 400 # Bad Request

    # 2. Validar o formato básico dos dados recebidos
    if not isinstance(lista_cookies_recebida, list):
        logging.warning(f"Dados recebidos não são uma lista: {type(lista_cookies_recebida)}")
        return jsonify({"success": False, "message": "Erro: Corpo da requisição deve ser uma lista (array JSON) de cookies."}), 400 # Bad Request

    #logging.info(f"Recebida lista com {len(lista_cookies_recebida)} cookies para validação.")

    # 3. Chamar a função de validação e salvamento
    try:
        # A função validar_e_salvar_cookies retorna True se validou e salvou, False caso contrário.
        sucesso = validar_e_salvar_cookies(lista_cookies_recebida)

        if sucesso:
            logging.info("Cookies validados e salvos com sucesso.")
            # Retorna 200 OK indicando que a operação foi processada e os cookies eram válidos/foram salvos.
            return jsonify({"success": True, "message": "Cookies válidos e salvos com sucesso."}), 200
        else:
            logging.info("Cookies recebidos foram considerados inválidos ou houve erro ao salvar.")
            # Retorna 200 OK, mas indica falha na validação/salvamento no corpo.
            # Usar 200 aqui significa que a requisição foi processada corretamente,
            # mas o resultado da *validação* dos cookies foi negativo.
            # Alternativamente, poderia usar 422 Unprocessable Entity se preferir.
            return jsonify({"success": False, "message": "Cookies inválidos ou erro ao salvar."}), 200

    except Exception as e:
        # Captura qualquer erro inesperado dentro de validar_e_salvar_cookies
        logging.error(f"Erro inesperado durante a execução de validar_e_salvar_cookies: {e}", exc_info=True) # Loga o traceback
        return jsonify({"success": False, "message": "Erro interno no servidor durante o processamento."}), 500 # Internal Server Error



@app.route('/api/requisicoes/<string:os_numero>/preparar', methods=['GET'])
def preparar_requisicao(os_numero):
    """
    Endpoint para buscar os dados iniciais necessários para o formulário de requisição de peças.
    """
    #logging.info(f"Sessão em preparar_requisição: {dict(session)}")
    if not os_numero:
        return jsonify({"success": False, "message": "Número da OS não fornecido."}), 400

    try:
        # Chama a função do backend que prepara os dados
        resultado_preparacao = preparar_dados_para_formulario_requisicao(os_numero)

        if resultado_preparacao.get("success"):
            return jsonify(resultado_preparacao), 200
        else:
            # Mapeia tipos de erro internos para status HTTP, se necessário
            error_type = resultado_preparacao.get("error_type")
            status_code = 500 # Padrão para erro genérico
            if error_type in ["StatusError", "BudgetError"]:
                status_code = 400 # Erro de validação/regra de negócio
            return jsonify(resultado_preparacao), status_code

    except Exception as e:
        # Captura erros inesperados na camada da rota
        print(f"Erro inesperado em /api/requisicoes/{os_numero}/preparar: {e}")
        return jsonify({
            "success": False,
            "error_type": "UnhandledException",
            "message": f"Erro interno no servidor ao preparar dados: {str(e)}"
        }), 500


# No início do seu arquivo principal (junto com os outros sets/locks)
requisicoes_em_processamento = set()
# Você pode usar o mesmo 'lock' do multiprocessing que já tem

@app.route('/api/requisicoes/<string:os_numero>/executar', methods=['POST'])
def executar_requisicao(os_numero):
    """
    Endpoint para receber dados e iniciar o processamento da requisição
    em background via multiprocessing, usando o padrão existente.
    """
    #logging.info(f"Sessão em executar_requisicao: {dict(session)}")
    # 1. Validar OS da URL
    if not os_numero:
        logging.warning("Executar Requisição: Número da OS não fornecido na URL.")
        return jsonify({"success": False, "message": "Número da OS não fornecido na URL."}), 400

    # 2. Obter SID da sessão
    sid = session.get('sid')
    if not sid:
         logging.error(f"Executar Requisição [{os_numero}]: SID não encontrado na sessão.")
         #return jsonify({"success": False, "message": "Erro interno: Sessão SocketIO não encontrada."}), 500

    # 3. Obter dados JSON
    dados_recebidos = request.get_json()
    if not dados_recebidos:
        logging.warning(f"Executar Requisição [{os_numero}]: Nenhum dado JSON recebido.")
        return jsonify({"success": False, "message": "Nenhum dado JSON recebido no corpo da requisição."}), 400

    # 4. Adicionar OS aos dados (se não vier no JSON, ou para garantir)
    dados_recebidos['os'] = os_numero

    # 5. Verificar/Controlar Processamento (usando o mesmo lock)
    with lock:
        if os_numero in requisicoes_em_processamento:
            logging.warning(f"Executar Requisição [{os_numero}]: Requisição já em processamento.")
            return jsonify({"success": False, "message": f"Requisição para OS {os_numero} já está em processamento."}), 409 # Conflict
        # Adiciona ao set ANTES de iniciar o processo
        requisicoes_em_processamento.add(os_numero)
        #logging.info(f"Executar Requisição [{os_numero}]: Adicionado ao set 'requisicoes_em_processamento'.")

    # 6. Iniciar Processo
    try:
        #logging.info(f"Executar Requisição [{os_numero}]: Iniciando Process para 'processar_submissao_requisicao_para_fila'.")
        # Chama a função adaptada que usa a fila
        t = threading.Thread(target=processar_submissao_requisicao_para_fila,
                    args=(dados_recebidos.copy(), sid, progress_queue, lock, requisicoes_em_processamento))
                    # Passa lock e o set para a função poder limpar ao final
        t.start()

        # 7. Retornar Resposta Imediata
        logging.info(f"Executar Requisição [{os_numero}]: Processo iniciado. Retornando 202.")
        return jsonify({
            "success": True,
            "message": "Requisição recebida e iniciada. Acompanhe o status."
        }), 202

    except Exception as e:
        # Limpar o set em caso de erro ao iniciar o processo
        logging.error(f"Executar Requisição [{os_numero}]: Erro ao iniciar Process: {e}", exc_info=True)
        with lock:
            if os_numero in requisicoes_em_processamento:
                requisicoes_em_processamento.remove(os_numero)
        return jsonify({"success": False, "message": f"Erro interno ao iniciar tarefa de requisição: {str(e)}"}), 500


# --- ROTAS PARA GERENCIAMENTO DE USUÁRIOS ---
@app.route('/api/usuarios', methods=['POST'])
def add_usuario():
    """
    Endpoint para cadastrar um novo usuário COS.
    Espera um JSON no corpo com: {"nome": "...", "user": "...", "senha": "..."}
    """
    dados_usuario = request.get_json()

    # 1. Validação básica dos dados recebidos
    if not dados_usuario:
        return jsonify({"success": False, "message": "Erro: Nenhum dado JSON recebido."}), 400

    nome = dados_usuario.get('nome')
    user = dados_usuario.get('user')
    senha = dados_usuario.get('senha')

    if not nome or not user or not senha:
        campos_faltando = []
        if not nome: campos_faltando.append("nome")
        if not user: campos_faltando.append("user")
        if not senha: campos_faltando.append("senha")
        return jsonify({
            "success": False,
            "message": f"Erro: Campos obrigatórios faltando: {', '.join(campos_faltando)}."
        }), 400

    # 2. Chamar a função de backend para cadastrar
    try:
        # Monta o dicionário exatamente como a função espera (se necessário)
        # Neste caso, dados_usuario já deve estar no formato correto.
        # --- Certifique-se que 'cadastrar_login' está importada! ---
        sucesso_cadastro = cadastrar_login(dados_usuario)

        if sucesso_cadastro:
            # Código 201 Created é apropriado para criação bem-sucedida
            return jsonify({
                "success": True,
                "message": f"Usuário '{nome}' cadastrado com sucesso."
            }), 201
        else:
            # A função retornou False, indicando falha (ex: usuário já existe?)
            # Código 409 Conflict pode ser apropriado se for por usuário existente
            return jsonify({
                "success": False,
                "message": f"Falha ao cadastrar usuário '{nome}'. Verifique se já existe ou os dados são válidos."
            }), 409 # Ou 400 se for um erro de dados inválidos

    except NameError:
         # Captura especificamente o erro se cadastrar_login não foi importada
         print("ERRO CRÍTICO: Função 'cadastrar_login' não foi encontrada/importada!")
         return jsonify({
            "success": False,
            "message": "Erro interno no servidor: Função de cadastro não encontrada."
         }), 500
    except Exception as e:
        # Captura outros erros inesperados na função cadastrar_login
        print(f"Erro interno ao chamar cadastrar_login para {nome}: {e}")
        import traceback
        traceback.print_exc() # Log completo do erro no console do servidor
        return jsonify({
            "success": False,
            "message": f"Erro interno no servidor ao cadastrar usuário: {str(e)}"
        }), 500

@app.route('/api/usuarios', methods=['GET'])
def get_usuarios():
    """
    Endpoint para listar todos os nomes de usuários cadastrados.
    """
    try:
        lista_usuarios = listar_nomes_usuarios()
        return jsonify(lista_usuarios), 200
    except Exception as e:
        print(f"Erro ao listar usuários: {e}")
        return jsonify({"success": False, "message": f"Erro interno ao listar usuários: {str(e)}"}), 500


@app.route('/api/usuarios/<string:nome_usuario>', methods=['DELETE'])
def delete_usuario(nome_usuario):
    """
    Endpoint para deletar um usuário específico.
    """
    if not nome_usuario:
        return jsonify({"success": False, "message": "Nome do usuário não fornecido."}), 400

    try:
        sucesso = deletar_usuario(nome_usuario)
        if sucesso:
            return jsonify({"success": True, "message": f"Usuário '{nome_usuario}' deletado com sucesso."}), 200
            # Alternativamente, poderia retornar status 204 No Content sem corpo de resposta
        else:
            # A função deletar_usuario poderia ser mais específica (ex: retornar se não encontrou)
            # Aqui assumimos que False significa falha geral ou usuário não encontrado.
             return jsonify({"success": False, "message": f"Falha ao deletar usuário '{nome_usuario}' (pode não existir ou erro interno)."}), 404 # Ou 500 dependendo da causa

    except Exception as e:
        print(f"Erro ao deletar usuário {nome_usuario}: {e}")
        return jsonify({"success": False, "message": f"Erro interno ao deletar usuário: {str(e)}"}), 500


@app.route('/api/usuarios/<string:nome_usuario>/login', methods=['GET'])
def get_login_usuario(nome_usuario):
    """
    Endpoint para recuperar dados de login (usuário e senha) de um usuário.
    *** ATENÇÃO: EXPOR SENHAS DIRETAMENTE É EXTREMAMENTE INSEGURO! ***
    *** CONSIDERE ALTERNATIVAS COMO RESET DE SENHA OU TOKENS. ***
    """
    if not nome_usuario:
        return jsonify({"success": False, "message": "Nome do usuário não fornecido."}), 400

    # !!! ADICIONE AQUI VERIFICAÇÕES DE SEGURANÇA REAIS !!!
    # Ex: Verificar se o solicitante tem permissão para ver esses dados.
    # Isso é crucial porque esta rota é muito sensível.

    try:
        login_info = recuperar_login(nome_usuario)
        if login_info and 'user' in login_info and 'senha' in login_info:
            #print(f"AVISO DE SEGURANÇA: Recuperando login para {nome_usuario} via API.") # Log para auditoria
            return jsonify(login_info), 200
        else:
            return jsonify({"success": False, "message": f"Login para usuário '{nome_usuario}' não encontrado."}), 404

    except Exception as e:
        print(f"Erro ao recuperar login para {nome_usuario}: {e}")
        return jsonify({"success": False, "message": f"Erro interno ao recuperar login: {str(e)}"}), 500



def verificar_saw_pendente(numero_os, categoria):
    numero_os = numero_os.strip()
    user = "Luciano Oliveira"
    sessao = carregar_sessao(user)

    if len(numero_os) == 10:
        ordem = obter_os_correspondentes(numero_os)
        numero_os = ordem
    
    url = "http://192.168.25.131:8080/COS_CSO/SawControl"
    categoria_map = {
        "oxidacao": "SRC73",
        "uso_excessivo": "SRC29",
        "os_mista": "SRC29",
        "pecas_cosmeticas": "SRZ15"
    }
    categoria_saw = categoria_map.get(categoria, "SRC29")

    params = {
        "acao": "verificarSePossuiSAWAbertoParaOS",
        "IP": "192.168.25.216",
        "IDUsuario": "1417",
        "NumeroOS": numero_os,
        "CategoriaSAW": categoria_saw
    }

    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/SolicitarSAW.jsp?NumeroOS={numero_os}&tipoServico=BAL&motivoOS=S02",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = sessao.get(url, params=params, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result.get("Sucesso", False) and result.get("Mensagem") == "Ok"
    except Exception as e:
        print(f"Erro ao verificar SAW pendente: {e}")
        return False

def enviar_solicitacao_saw(form_data):
    #print(form_data)
    url = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServicoGSPN"
    ip = "192.168.25.216"
    dados_os = coletar_dados_os(form_data['os'])
    tecnico = dados_os['tecnico']
    usuario = consultar_id_tecnico_cos(tecnico)
    id_usuario = usuario[1]
    atualizar_ag_saw = False
    numero_os = form_data['os']
    numero_os = numero_os.strip()
    sessao = carregar_sessao(tecnico)
    if len(numero_os) == 10:
        ordem = obter_os_correspondentes(numero_os)
        numero_os = ordem    
    # Montagem do dicionário saw_data
    saw_data = {
        "pecas": [{"pecaselecionada": part["code"], "motivoTrocaPeca": part["defect"], "id": i + 1} 
                  for i, part in enumerate(form_data["parts"])],
        "atualizarAgSaw": atualizar_ag_saw,
        "observacao": form_data["observations"]
    }
    
    print(f'Categoria recebida: {form_data["category"]}')
    if form_data["category"] == "oxidacao":
        saw_data["categoria"] = "SRC73"
        saw_data["sintoma"] = "T9C"
        saw_data["quantidade"] = 1
    elif form_data["category"] == "uso_excessivo":
        saw_data["categoria"] = "SRC29"
    elif form_data["category"] == "os_mista":
        saw_data["categoria"] = "SRC29"
    elif form_data["category"] == "pecas_cosmeticas":
        saw_data["categoria"] = "SRZ15"

    # Serializa o JSON garantindo que caracteres especiais sejam mantidos em UTF-8
    saw_json = json.dumps(saw_data, ensure_ascii=False)
    data_atual = datetime.now().strftime("%d%m%Y%H%M%S")

    # Montagem dos parâmetros
    params = {
        "Acao": "SolicitarSAW",
        "IP": ip,
        "IDUsuario": id_usuario,
        "NumeroOS": numero_os,
        "saw": saw_json,
        "DataAtualAlteracaoOS": data_atual
    }

    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/SolicitarSAW.jsp?NumeroOS={numero_os}&tipoServico=BAL&motivoOS=S02",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        # Faz a requisição GET com os parâmetros codificados corretamente
        response = sessao.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Erro ao enviar solicitação SAW: {e}")
        return {"Sucesso": False, "Mensagem": f"Erro ao enviar solicitação: {str(e)}"}


def processar_os(os_gspn, sid, queue):
    """
    Processa a sincronização de peças para uma OS GSPN,
    atualizando o status via queue e gerenciando o estado
    no set global 'os_em_processamento' de forma thread-safe.
    """
    os_original = os_gspn # Guarda a OS original para logs e remoção
    os_gspn = os_gspn.strip()
    driver = None # Inicializa driver como None

    try:
        # Converte OS de 6 dígitos se necessário ANTES de adicionar ao set/queue
        if len(os_gspn) == 6:
            #logging.info(f"OS GSPN {os_gspn} tem 6 dígitos, buscando correspondente...")
            ordem = obter_os_correspondentes(os_gspn)
            if ordem:
                #logging.info(f'OS GSPN {os_gspn} corresponde a {ordem}. Usando {ordem}.')
                os_para_processar = ordem
            else:
                logging.error(f'Não foi possível obter OS correspondente para {os_gspn}. Abortando.')
                # Envia status de falha imediatamente se não encontrar a OS
                queue.put({'os': os_original, 'step': 'Erro Inicial', 'status': 'failed', 'error': f'Não encontrada OS correspondente para {os_gspn}', 'sid': sid})
                # Não precisa remover do set, pois não foi adicionada
                return # Termina a execução da função aqui
        else:
             os_para_processar = os_gspn

        # Envia status inicial usando a OS que será processada
        queue.put({'os': os_para_processar, 'step': 'Iniciando', 'status': 'running', 'sid': sid})

        # Chama a função principal de sincronização
        sucesso = sincronizar_pecas(os_para_processar, sid, queue)

        #if sucesso:
            #queue.put({'os': os_para_processar, 'step': 'Tudo certo', 'status': 'completed', 'sid': sid})
            #time.sleep(0.8) # Pequena pausa opcional
        #else:
            # Se sincronizar_pecas retorna False, é uma falha controlada
            #queue.put({'os': os_para_processar, 'step': 'Processo concluído com falha', 'status': 'failed', 'error': 'Falha reportada por sincronizar_pecas', 'sid': sid})

    except Exception as e:
        logging.error(f"Erro inesperado ao processar OS {os_para_processar if 'os_para_processar' in locals() else os_original}: {e}", exc_info=True)
        # Usa 'os_para_processar' se definido, senão 'os_original' para o log de erro
        os_no_erro = os_para_processar if 'os_para_processar' in locals() else os_original
        queue.put({'os': os_no_erro, 'step': 'Erro geral no processamento', 'status': 'failed', 'error': str(e), 'sid': sid})

    finally:
        # Usa o lock e o set globais para remover a OS da lista de processamento
        # Garante que removerá a mesma OS que foi adicionada (a original ou a convertida)
        os_a_remover = os_para_processar if 'os_para_processar' in locals() else os_original

        with lock: # Usa o lock global
            if os_a_remover in os_em_processamento: # Usa o set global
                os_em_processamento.remove(os_a_remover) # Usa o set global
                #logging.info(f"OS {os_a_remover} removida do set de processamento (Thread).")
            else:
                # Isso pode acontecer se a função retornou antes do finally por um erro inicial
                # ou se houve algum problema ao adicionar ao set.
                logging.warning(f"Tentativa de remover OS {os_a_remover} que não estava no set (Thread).")

@app.route('/')
def index():
    return render_template('index.html')



@app.route('/api/submit_os', methods=['POST'])
def submit_os():
    data = request.get_json()
    os_gspn = data.get('os_gspn')
    sid = session.get('sid')
    if not os_gspn:
        return jsonify({'status': 'error', 'message': 'OS não fornecida'}), 400

    with lock: # Usa o lock global
        if os_gspn in os_em_processamento: # Usa o set global
            return jsonify({'status': 'error', 'message': f'OS {os_gspn} já está sendo processada'}), 409
        os_em_processamento.add(os_gspn) # Usa o set global
        #logging.info(f"OS {os_gspn} adicionada ao set de processamento (Thread).")

    # Cria e inicia uma Thread em vez de Process
    # Não passa mais a lista e o lock (usa globais)
    t = threading.Thread(target=processar_os, args=(os_gspn, sid, progress_queue)) #
    t.start() # Inicia a thread
    return jsonify({'status': 'success', 'message': f'OS {os_gspn} enviada para processamento'})

@app.route('/status', methods=['GET'])
def status():
    with lock: # Usa o lock global
        em_processamento = list(os_em_processamento) # Lê o set global
    return jsonify({'em_processamento': em_processamento})

@app.route('/api/saw_data', methods=['GET', 'OPTIONS'])
def get_saw_data():
    sessao = carregar_sessao("Luciano Oliveira")
    os = request.args.get('os')
    os = os.strip()
    if len(os) == 10:
        os_cos = obter_os_correspondentes(os)
        os = os_cos
    category = request.args.get('category')
    if not os or not category:
        return jsonify({'status': 'error', 'message': 'OS ou categoria não fornecida'}), 400
    try:
        data = filtrar_dados_saw(os, category)
        return jsonify({'status': 'success', 'data': data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro ao buscar dados: {str(e)}'}), 500

@app.route('/api/check_saw_pendente', methods=['GET'])
def check_saw_pendente():
    os = request.args.get('os')
    category = request.args.get('category')
    if not os or not category:
        return jsonify({'status': 'error', 'message': 'OS ou categoria não fornecida'}), 400
    can_proceed = verificar_saw_pendente(os, category)
    return jsonify({'status': 'success', 'can_proceed': can_proceed})

@app.route('/api/submit_saw', methods=['POST'])
def submit_saw():
    form_data = request.get_json()
    if not form_data or 'os' not in form_data or 'category' not in form_data or 'parts' not in form_data:
        return jsonify({'status': 'error', 'message': 'Dados incompletos'}), 400
    print(f"Dados recebidos para SAW: {form_data}")
    result = enviar_solicitacao_saw(form_data)
    if result.get("Sucesso", False):
        return jsonify({'status': 'success', 'message': result.get("Mensagem", "Criado com sucesso")})
    else:
        return jsonify({'status': 'error', 'message': result.get("Mensagem", "Erro desconhecido")}), 500

# --- ROTA PARA GERENCIAR (FINALIZAR/CRIAR) OS GSPN ---

@app.route('/api/gspn/gerenciar_os', methods=['POST'])
def handle_gerenciar_os_gspn():
    """
    Endpoint para gerenciar Ordens de Serviço (OS) no GSPN.
    Pode finalizar uma OS existente, criar uma nova, ou ambos em sequência.
    Recebe os parâmetros via JSON no corpo da requisição.

    JSON esperado no corpo:
    {
        "finalizar": True/False,          # Opcional, default False
        "gerar_os": True/False,           # Opcional, default False
        "numero_os": "NUMERO_DA_OS..."    # Obrigatório se finalizar=True, opcional para gerar_os
        # ... outros dados que 'criar_ordem_servico' possa precisar dentro de gspn_manager
    }

    Retorna:
        JSON com {"sucesso": True/False, "mensagem": "...", "os_gspn": "NOVA_OS" (se criada)}
    """
    # 1. Validação do Content-Type
    if not request.is_json:
        logging.warning("Rota /api/gspn/gerenciar_os: Requisição sem Content-Type application/json")
        return jsonify({"sucesso": False, "mensagem": "Erro: Content-Type deve ser application/json."}), 415 # Unsupported Media Type

    # 2. Obtenção e validação básica dos dados JSON
    try:
        dados_formulario = request.get_json()
        if not dados_formulario: # Garante que o corpo JSON não seja vazio
            logging.warning("Rota /api/gspn/gerenciar_os: Corpo JSON vazio recebido.")
            return jsonify({"sucesso": False, "mensagem": "Erro: Corpo da requisição JSON não pode ser vazio."}), 400 # Bad Request
    except Exception as e:
        logging.error(f"Rota /api/gspn/gerenciar_os: Erro ao fazer parse do JSON: {e}")
        return jsonify({"sucesso": False, "mensagem": "Erro: JSON inválido na requisição."}), 400 # Bad Request

    # 3. Chamada da função principal e tratamento do resultado
    try:
        logging.info(f"Rota /api/gspn/gerenciar_os: Recebido para gerenciar: {dados_formulario}")

        # --- Chama a função lógica que faz o trabalho pesado ---
        resultado = gerenciar_os_gspn_sequencial(dados_formulario)
        # -------------------------------------------------------

        logging.info(f"Rota /api/gspn/gerenciar_os: Resultado da gerencia: {resultado}")

        # Define o status HTTP com base no sucesso retornado pela função lógica
        if resultado.get("sucesso"):
            status_code = 200 # Operação(ões) bem-sucedida(s)
        else:
            # A função lógica indicou uma falha (validação, erro em sub-etapa, etc.)
            # Usar 400 Bad Request é apropriado para erros lógicos ou de validação originados dos dados.
            status_code = 400

        return jsonify(resultado), status_code

    except NameError as ne:
         # Captura especificamente o erro se a função não foi importada/encontrada
         logging.error("ERRO CRÍTICO: Função 'gerenciar_os_gspn_sequencial' não foi encontrada/importada!", exc_info=True)
         return jsonify({"sucesso": False, "mensagem": "Erro interno no servidor: Função de gerenciamento não encontrada."}), 500
    except Exception as e:
        # Captura erros inesperados DENTRO de gerenciar_os_gspn_sequencial ou na comunicação
        logging.exception("Rota /api/gspn/gerenciar_os: Erro inesperado durante o processamento.") # Loga o traceback completo
        return jsonify({"sucesso": False, "mensagem": f"Erro interno inesperado no servidor: {str(e)}"}), 500 # Internal Server Error

# --- FIM DA NOVA ROTA ---

@socketio.on('connect')
def handle_connect():
    session['sid'] = request.sid
    session.modified = True  # Garante que a sessão seja atualizada
    #logging.info(f"Cliente conectado: {request.sid}")
    #logging.info(f"Sessão após conectar: {dict(session)}")  # Para depuração



def progress_listener():
    while True:
        message = progress_queue.get()
        if 'sid' in message and 'os' in message:
            # Determina o tipo de evento com base em uma chave (ex.: 'type')
            event_type = message.get('type', 'progress')  # 'progress' como padrão
            socketio.emit(event_type, {
                'os': message['os'],
                'step': message['step'],
                'status': message['status'],
                'error': message.get('error', '')
            }, room=message['sid'])
        else:
            print(f"Mensagem sem SID ou OS: {message}")

if __name__ == '__main__':
    threading.Thread(target=progress_listener, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)