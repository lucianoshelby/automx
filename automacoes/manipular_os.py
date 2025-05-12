from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
#import automacoes.abrir_os as abrir_os
from automacoes.utilidades import fechar_popups, esperar_popup
import time
from automacoes.cos.coletar_dados_cos import coletar_usadas_cos, obter_os_correspondentes
from selenium.webdriver.common.keys import Keys

def mudar_status_ag_custo_reparo(driver):
    """Altera o status da OS para 'Aguardando confirmação do consumidor' no GSPN.""
    
    print(f"\n🔄 Mudando status da OS GSPN {os_gspn} para 'AG CUSTO DE REPARO'...")
    abrir_os.abrir_os_gspn(driver, os_gspn)
    # 🟢 Garantir que estamos na aba correta da OS do GSPN
    for aba in driver.window_handles:
        driver.switch_to.window(aba)
        if os_gspn in driver.current_url:
            print(f"✅ Encontrada a aba correta para a OS {os_gspn}.")
            break

    # 🟢 Expandir tabelas e aguardar carregamento correto
    try:
        print("📂 Expandindo tabelas...")
        driver.find_element(By.XPATH, "//tr[@onclick=\"javascript: toggleTable('Main');\"]").click()
        if esperar_elemento_visivel(driver, "//div[@id='divMain']", timeout=5):
            print("✅ Tabela 'Informações gerais' expandida.")

        # 🟢 Expandir a tabela "Informações do Produto" e aguardar o botão "Verificar Garantia"
        driver.find_element(By.XPATH, "//tr[@onclick=\"javascript: initProductTab();\"]").click()
        if esperar_elemento_clicavel(driver, "//input[@id='wtyCheckBtn']", timeout=10):
            print("✅ Tabela 'Informações do Produto' expandida com sucesso e botão 'Verificar Garantia' está pronto.")
            time.sleep(2)
    except NoSuchElementException:
        print("⚠️ Não foi possível expandir algumas tabelas.")

    # 🟢 Verificar o "Status da Garantia"
    try:
        status_garantia = driver.find_element(By.ID, "IN_OUT_WTY").get_attribute("value").strip()
        print(f"📌 Status da Garantia: {status_garantia}")

        if "LP" in status_garantia:
            print("⚠️ Garantia LP detectada. Aplicando VOID3...")

            # Selecionar VOID3 na lista de exceções
            select_void = Select(driver.find_element(By.ID, "WTY_EXCEPTION"))
            select_void.select_by_value("VOID3")

            # Clicar no botão "Verificar garantia"
            driver.find_element(By.ID, "wtyCheckBtn").click()

            # 🟢 Aguardar popups e fechar
            esperar_popup(driver)

            print("✅ VOID aplicado com sucesso.")

    except NoSuchElementException:
        print("❌ Não foi possível verificar o status da garantia.")"""
    # 🟢 4. Verificar o "Status da OS no GSPN"
    try:
        select_status = Select(driver.find_element(By.ID, "STATUS"))
        status_atual = select_status.first_selected_option.text.strip()

        print(f"📌 Status da OS no GSPN: {status_atual}")

        if status_atual != "Pendente":
            print("⚠️ Status não está 'Pendente'. Alterando para 'Pendente'...")
            select_status.select_by_visible_text("Pendente")
            time.sleep(2)

    except NoSuchElementException:
        print("❌ Não foi possível verificar o status da OS.")

    # 🟢 5. Mudar o "Motivo da Pendência"
    try:
        select_motivo = Select(driver.find_element(By.ID, "REASON"))
        #
        # Procurar a opção "Aguardando confirmação do consumidor"
        opcoes = [option.text.strip() for option in select_motivo.options]

        if "Aguardando confirmação do custo de reparo[HP080]" in opcoes:
            #
            select_motivo.select_by_visible_text("Aguardando confirmação do custo de reparo[HP080]")
            print("✅ Motivo da pendência alterado para 'Aguardando confirmação do consumidor'.")
        else:
            print("⚠️ Opção 'Aguardando confirmação do consumidor' não encontrada. Aplicando solução alternativa...")

            # Alterar Status para "Técnico designado" e depois voltar para "Pendente"
            select_status.select_by_visible_text("Técnico designado")
            time.sleep(2)
            select_status.select_by_visible_text("Pendente")
            time.sleep(2)

            # Tentar novamente selecionar o motivo da pendência
            # Localizar e clicar no dropdown para expandi-lo
            dropdown_reason = driver.find_element(By.ID, "REASON")
            dropdown_reason.click()
            time.sleep(1)  # Pequena pausa para garantir que a lista carregue
            select_motivo.select_by_visible_text("Aguardando confirmação do custo de reparo[HP080]")
            print("✅ Ajuste feito com sucesso.")

    except NoSuchElementException:
        print("❌ Não foi possível alterar o motivo da pendência.")

    # 🟢 6. Clicar no botão relógio
    try:
        botao_relogio = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@id='divRepair']//td[@id='serviceDateTD2_LAST_APP']//img[@src='/img/ico_time.gif']")))
        #botao_relogio = driver.find_element(By.XPATH, "//img[@src='/img/ico_time.gif']")
        botao_relogio.click()
        time.sleep(1)
        print("✅ Data e hora atualizadas usando o botão relógio.")
    except:
        print("⚠️ Botão relógio não encontrado.")

    # 🟢 7. Clicar no botão "Salvar"
    try:
        driver.find_element(By.ID, "btnSave").click()
        print("💾 Salvando alterações...")

        # Chamando a função para fechar popups
        esperar_popup(driver, timeout=5)
        time.sleep(3)
        esperar_popup(driver)
        if fechar_popups(driver, timeout=5):
            esperar_popup(driver, timeout=3)
            print("✅ Processo finalizado com sucesso.")
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(2)
        else:
            
            print("❌ Falha ao salvar: nenhum popup detectado após 2 minutos.")

    except NoSuchElementException:
        print("❌ Não foi possível clicar no botão 'Salvar'.")



