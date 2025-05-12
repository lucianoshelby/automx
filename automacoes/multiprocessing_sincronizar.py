from multiprocessing import Process, Manager
from config import configurar_driver  # Configuração do WebDriver
import time
from .pecas import sincronizar_pecas  # Função que realiza a sincronização

def executar_sincronizacao(os_gspn, os_em_processamento):
    """Cria uma nova instância do Selenium e executa a sincronização."""
    
    # 🔹 Verifica se a OS já está sendo processada
    if os_gspn in os_em_processamento:
        print(f"⚠️ A OS {os_gspn} já está em processamento. Ignorando...")
        return

    # 🔹 Marca a OS como em processamento
    os_em_processamento[os_gspn] = True
    print(f"🚀 Iniciando processamento da OS {os_gspn}...")

    try:
        # 🔹 Cada processo cria sua própria instância do WebDriver
        driver = configurar_driver()
        
        # 🔹 Executa a função de sincronização
        sincronizar_pecas(driver, os_gspn)

    finally:
        # 🔹 Garante que o WebDriver seja fechado corretamente
        driver.quit()
        print(f"✅ OS {os_gspn} concluída e removida da fila de processamento.")
        
        # 🔹 Remove a OS do controle quando terminar
        del os_em_processamento[os_gspn]

if __name__ == "__main__":
    ordens_de_servico = ["4172219920", "4172240794"]  # Exemplo (a OS "12345" aparece 2 vezes)

    # 🔹 Criamos um dicionário compartilhado para rastrear as OSs em processamento
    with Manager() as manager:
        os_em_processamento = manager.dict()  
        processos = []

        # Criar um processo para cada OS
        for os_gspn in ordens_de_servico:
            p = Process(target=executar_sincronizacao, args=(os_gspn, os_em_processamento))
            p.start()
            processos.append(p)

        # Esperar todos os processos terminarem
        for p in processos:
            p.join()

    print("🎯 Todas as sincronizações foram concluídas!")
