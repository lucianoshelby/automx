import base64
import json
import os

# Arquivo onde os dados serão salvos
ARQUIVO_DADOS = ".\\login do cos\\logins.json"

def cadastrar_login(dados: dict) -> bool:
    """
    Cadastra um novo login com nome, usuário e senha (codificada em base64).
    Retorna True se cadastrado com sucesso, False se o usuário já existe.
    """
    # Verifica se os campos necessários estão presentes
    if not all(key in dados for key in ['nome', 'user', 'senha']):
        return False
    
    # Carrega dados existentes
    dados_existentes = {}
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r') as f:
            dados_existentes = json.load(f)
    
    # Verifica se o usuário já existe
    if dados['user'] in [info['user'] for info in dados_existentes.values()]:
        return False
    
    # Codifica a senha em base64
    senha_codificada = base64.b64encode(dados['senha'].encode()).decode('utf-8')
    
    # Adiciona novo registro
    dados_existentes[dados['nome']] = {
        'user': dados['user'],
        'senha_codificada': senha_codificada
    }
    
    # Salva no arquivo
    with open(ARQUIVO_DADOS, 'w') as f:
        json.dump(dados_existentes, f, indent=4)
    
    return True

def recuperar_login(nome: str) -> dict:
    """
    Retorna o login e a senha original (decodificada) para o nome fornecido.
    Retorna dict vazio se não encontrado.
    """
    # Carrega dados existentes
    if not os.path.exists(ARQUIVO_DADOS):
        return {}
    
    with open(ARQUIVO_DADOS, 'r') as f:
        dados_existentes = json.load(f)
    
    # Verifica se o nome existe
    if nome not in dados_existentes:
        return {}
    
    # Decodifica a senha de base64 para texto simples
    senha_original = base64.b64decode(dados_existentes[nome]['senha_codificada']).decode('utf-8')
    
    return {
        'user': dados_existentes[nome]['user'],
        'senha': senha_original
    }


def deletar_usuario(nome: str) -> bool:
    """
    Deleta o usuário com o nome fornecido.
    Retorna True se deletado com sucesso, False se o usuário não existe.
    """
    # Verifica se o arquivo existe
    if not os.path.exists(ARQUIVO_DADOS):
        return False
    
    # Carrega dados existentes
    with open(ARQUIVO_DADOS, 'r') as f:
        dados_existentes = json.load(f)
    
    # Verifica se o nome existe
    if nome not in dados_existentes:
        return False
    
    # Remove o usuário
    del dados_existentes[nome]
    
    # Salva o arquivo atualizado
    with open(ARQUIVO_DADOS, 'w') as f:
        json.dump(dados_existentes, f, indent=4)
    print(f'Usuário {nome} deletado com sucesso.')
    return True

def listar_nomes_usuarios() -> list[str]:
    """
    Lê o arquivo de dados e retorna uma lista com os nomes dos usuários cadastrados.

    Retorna:
        list[str]: Uma lista contendo os nomes (chaves do JSON) dos usuários.
                   Retorna uma lista vazia se o arquivo não existir, estiver vazio
                   ou ocorrer um erro ao ler o JSON.
    """
    # Verifica se o arquivo de dados existe
    if not os.path.exists(ARQUIVO_DADOS):
        print(f"Aviso: Arquivo de dados '{ARQUIVO_DADOS}' não encontrado.")
        return []  # Retorna lista vazia se o arquivo não existe

    try:
        # Tenta abrir e carregar os dados do arquivo JSON
        with open(ARQUIVO_DADOS, 'r') as f:
            # Verifica se o arquivo está vazio antes de tentar carregar
            if os.path.getsize(ARQUIVO_DADOS) == 0:
                print(f"Aviso: Arquivo de dados '{ARQUIVO_DADOS}' está vazio.")
                return [] # Retorna lista vazia se o arquivo estiver vazio
            
            dados_existentes = json.load(f)

        # Os nomes dos usuários são as chaves do dicionário principal carregado do JSON.
        # O método .keys() retorna uma visão das chaves, convertemos para lista.
        nomes = list(dados_existentes.keys())
        return nomes

    except json.JSONDecodeError:
        # Se o arquivo não for um JSON válido (ex: corrompido)
        print(f"Erro: O arquivo '{ARQUIVO_DADOS}' não pôde ser decodificado (JSON inválido).")
        return []  # Retorna lista vazia em caso de erro de decodificação
    except Exception as e:
        # Captura outros possíveis erros de leitura/processamento
        print(f"Ocorreu um erro inesperado ao ler o arquivo '{ARQUIVO_DADOS}': {e}")
        return []


if __name__ == "__main__":
    # Exemplo de uso
    nomes = listar_nomes_usuarios()
    print("Usuários cadastrados:", nomes)
