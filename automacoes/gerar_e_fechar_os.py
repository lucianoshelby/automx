import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
from automacoes.finalizar_os.finalizar_sem_reparo import aplicar_reparo_completo_remontagem, aplicar_produto_entregue
from automacoes.vincular_os.designar_tecnico import designar_tecnico_gspn
from automacoes.vincular_os.gerar_os_gspn import criar_ordem_servico
from automacoes.cos.coletar_dados_cos import obter_os_correspondentes
from automacoes.finalizar_os.anexos_gspn import checar_e_anexar_obrigatorios
from automacoes.cos.auto_cos import deletar_cos


'''def criar_e_fechar_os_gspn(formulario):
    """
    Função para criar ou fechar uma ordem de serviço no sistema GSPN.
    Recebe um dicionário com o número da OS, e a tarefa a ser realizada.
    Retorna um dicionario com "sucesso" = True ou False e a mensagem de erro, se houver.
    Se a tarefa for "criar", o dicionário deve conter o número da nova OS.
    """

    finalizar = formulario.get("finalizar", False)
    gerar_os = formulario.get("gerar_os", False)
    numero_os = formulario.get("numero_os", None)


    if len(numero_os) == 10:
        try:
            os_cos = obter_os_correspondentes(numero_os)
            numero_os = os_cos
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Erro ao obter OS correspondentes: {e}"}
    
    # Se finalizar for True, chama a função de finalizar OS
    if finalizar:
        try:
            sucesso = aplicar_reparo_completo_remontagem(numero_os)
            if sucesso:
                print(f"OS {numero_os} finalizada com sucesso.")
            else:
                return {"sucesso": False, "mensagem": f"Erro ao finalizar a OS {numero_os}."}
            sucesso = aplicar_produto_entregue(numero_os)
            if sucesso:
                print(f"Produto entregue para a OS {numero_os} com sucesso.")
            else:
                return {"sucesso": False, "mensagem": f"Erro ao entregar o produto da OS {numero_os}."}
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Erro ao finalizar a OS {numero_os}: {e}"}
        
    # Se gerar_os for True, chama a função de criar OS
    if gerar_os:
        try:
            os_gspn = criar_ordem_servico(numero_os)
            if os_gspn:
                print(f"OS {os_gspn} criada com sucesso.")
            else:
                return {"sucesso": False, "mensagem": f"Erro ao criar a OS {numero_os}."}
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Erro ao criar a OS {numero_os}: {e}"}
        # chama a função de designar técnico
        try:
            sucesso = designar_tecnico_gspn(os_gspn)
            if sucesso:
                print(f"Técnico designado para a OS {os_gspn} com sucesso.")
            else:
                return {"sucesso": False, "mensagem": f"Erro ao designar técnico para a OS {os_gspn}."}
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Erro ao designar técnico para a OS {os_gspn}: {e}"}
        #chama a função de verificar anexos
        try:
            sucesso = checar_e_anexar_obrigatorios(os_gspn)
            if sucesso:
                print(f"Anexos obrigatórios verificados e anexados para a OS {os_gspn} com sucesso.")
            else:
                return {"sucesso": False, "mensagem": f"Erro ao verificar anexos obrigatórios para a OS {os_gspn}."}
        except Exception as e:
            return {"sucesso": False, "mensagem": f"Erro ao verificar anexos obrigatórios para a OS {os_gspn}: {e}"}
        
    if gerar_os:
        return {"sucesso": True, "os_gspn": os_gspn}
    else:
        return {"sucesso": True}'''

import logging

# (Keep logging setup and helper functions as defined before)
# ... (logging.basicConfig, obter_os_correspondentes, etc.) ...

def gerenciar_os_gspn_sequencial(formulario):
    """
    Gerencia ordens de serviço (OS) no GSPN: pode finalizar uma existente,
    criar uma nova, ou finalizar uma existente E criar uma nova em sequência.

    Ações são determinadas pelas chaves 'finalizar' e 'gerar_os'.
    Se ambas forem True, a finalização ocorre primeiro.

    Args:
        formulario (dict): Dicionário com os dados da operação. Espera-se:
            - 'finalizar' (bool): True para finalizar a OS em 'numero_os'. (Default: False)
            - 'gerar_os' (bool): True para criar uma nova OS. (Default: False)
            - 'numero_os' (str | None): O número da OS a ser finalizada (se 'finalizar' é True).
                                        Pode ser usado como base para 'gerar_os'.
                                        Obrigatório se 'finalizar' for True.
                                        Se tiver 10 dígitos, tentará obter a OS correspondente.
            - (outros dados podem ser necessários para 'criar_ordem_servico')

    Returns:
        dict: Resultado da operação:
            {
                "sucesso": bool,
                "mensagem": str | None,  # Presente em caso de erro.
                "os_gspn": str | None    # Presente se 'gerar_os' foi solicitado e bem-sucedido.
            }
    """
    finalizar = formulario.get("finalizar", False)
    gerar_os = formulario.get("gerar_os", False)
    numero_os_entrada = formulario.get("numero_os")

    # --- 1. Validação de Ação e Entradas Essenciais ---
    if not finalizar and not gerar_os:
        return {"sucesso": False, "mensagem": "Nenhuma ação especificada: 'finalizar' ou 'gerar_os' deve ser True."}
    if finalizar and not numero_os_entrada:
         return {"sucesso": False, "mensagem": "O 'numero_os' é obrigatório quando 'finalizar' é True."}

    
    os_criada = None # Para armazenar a nova OS, se gerada

    # --- 2. Pré-processamento do número da OS (se aplicável e necessário) ---
    # Só processa se houver um número de entrada (relevante para finalizar ou como base para criar)
    if numero_os_entrada and len(numero_os_entrada) == 10:
        #logging.info(f"Número OS '{numero_os_processado}' tem 10 dígitos. Buscando OS correspondente.")
        try:
            os_correspondente = obter_os_correspondentes(numero_os_entrada)
            logging.info(f"OS correspondente encontrada: '{os_correspondente}'")
            os_cos = os_correspondente # Atualiza o número a ser usado
            os_gspn = numero_os_entrada

        except Exception as e:
            msg = f"Erro ao obter OS correspondente para '{numero_os_entrada}': {e}"
            logging.error(msg)
            return {"sucesso": False, "mensagem": msg}
    elif len(numero_os_entrada) ==6:
        os_gspn = obter_os_correspondentes(numero_os_entrada)
        os_cos = numero_os_entrada
        logging.info(f"OS correspondente encontrada: '{os_gspn}'")
    # --- 3. Execução da Finalização (Se Solicitado) ---
    if finalizar:
        logging.info(f"Iniciando finalização da OS: {os_gspn}")
        try:
            # Passo 3.1: Aplicar reparo
            if not aplicar_reparo_completo_remontagem(os_gspn):
                msg = f"Falha ao aplicar reparo/remontagem para a OS {os_gspn}."
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"Reparo/remontagem aplicado com sucesso para OS {os_gspn}.")

            # Passo 3.2: Aplicar entrega
            if not aplicar_produto_entregue(os_gspn):
                msg = f"Falha ao registrar entrega do produto para a OS {os_gspn}."
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"Entrega registrada com sucesso para OS {os_gspn}.")

            try:
                deletar_cos(os_cos)
                logging.info(f"OS GSPN na OS {os_cos} deletada com sucesso.")
            except Exception as e:
                msg = f"Erro ao deletar COS para a OS {os_cos}: {e}"
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"OS {os_gspn} finalizada com sucesso.")
            # Não retorna ainda, pode precisar gerar nova OS

        except Exception as e:
            msg = f"Erro inesperado ao finalizar a OS {os_gspn}: {e}"
            logging.exception(msg)
            return {"sucesso": False, "mensagem": msg}

    # --- 4. Execução da Criação (Se Solicitado) ---
    if gerar_os:
        logging.info(f"Iniciando criação de nova OS (baseado em: {numero_os_entrada})")
        try:
            # Passo 4.1: Criar OS
            # Usa o numero_os_processado como base, conforme lógica original.
            # Adapte se precisar de outros dados do formulário.
            dados_para_criar = os_cos # Ou: formulario
            os_criada = criar_ordem_servico(dados_para_criar)
            if not os_criada:
                msg = f"Falha ao criar a nova OS no GSPN (baseado em: {dados_para_criar})."
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"Nova OS {os_criada} criada com sucesso no GSPN.")

            # Passo 4.2: Designar Técnico
            if not designar_tecnico_gspn(os_criada):
                msg = f"Falha ao designar técnico para a nova OS {os_criada}."
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"Técnico designado com sucesso para a nova OS {os_criada}.")

            # Passo 4.3: Checar/Anexar Obrigatórios
            if not checar_e_anexar_obrigatorios(os_criada):
                msg = f"Falha ao checar/anexar obrigatórios para a nova OS {os_criada}."
                logging.warning(msg)
                return {"sucesso": False, "mensagem": msg}
            logging.info(f"Anexos obrigatórios processados para a nova OS {os_criada}.")

            logging.info(f"Processo de criação da OS {os_criada} concluído com sucesso.")
            # Não retorna ainda, o retorno final decide o que incluir

        except Exception as e:
            msg_base = f"Erro inesperado durante processo de criação da nova OS (baseado em: {numero_os_entrada})"
            if os_criada: # Se a OS foi criada antes do erro
                 msg_base += f", após a OS {os_criada} ser parcialmente criada"
            msg = f"{msg_base}: {e}"
            logging.exception(msg)
            return {"sucesso": False, "mensagem": msg}

    # --- 5. Retorno Final ---
    # Se chegou aqui, todas as etapas solicitadas foram concluídas com sucesso.
    resultado = {"sucesso": True}
    if os_criada: # Se uma OS foi criada (ou seja, gerar_os era True e bem-sucedido)
        resultado["os_gspn"] = os_criada
    logging.info(f"Operação concluída com sucesso. Resultado: {resultado}")
    return resultado

if __name__ == "__main__":
    # Exemplo de uso da função
    formulario = {
        "finalizar": False,
        "gerar_os": True,
        "numero_os": "349377"  # Exemplo de número de OS
    }
    resultado = gerenciar_os_gspn_sequencial(formulario)
    print(resultado)