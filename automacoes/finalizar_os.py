# automacoes/finalizar_os.py

import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from . import abrir_os
from automacoes.utilidades import esperar_elemento_clicavel, esperar_popup, fechar_popups, localizar_aba_gspn
import os
import automacoes.cos.auto_cos as auto_cos

def confere_asc_job(driver, os_gspn):
    """Verifica e altera o campo ASC JOB se ele possuir 6 dígitos."""

    print(f"\n🔄 Conferindo campo ASC JOB da OS {os_gspn}")

    try:
        # 1️⃣ Capturar o valor atual do ASC_JOB_NO diretamente do input (sem expandir a tabela)
        print("🔍 Verificando o ASC_JOB_NO no campo de input...")

        campo_os = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ASC_JOB_NO"))
        )

        asc_job_no = campo_os.get_attribute("value").strip()

        print(f"📌 ASC_JOB_NO identificado: {asc_job_no}")

        # 2️⃣ Se o ASC_JOB_NO tiver **exatamente 6 caracteres**, corrigir
        if len(asc_job_no) == 6 or 'FG' in asc_job_no:
            print(f"⚠️ O ASC_JOB_NO ({asc_job_no}) está incorreto. Corrigindo...")

            # Expandir a tabela "Informações Gerais" **apenas se necessário**
            try:
                print("📂 Expandindo tabela 'Informações Gerais'...")
                driver.find_element(By.XPATH, "//tr[@onclick=\"javascript: toggleTable('Main');\"]").click()
                WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "divMain"))
                )
                print("✅ Tabela 'Informações Gerais' expandida.")
            except Exception as e:
                print(f"⚠️ Erro ao expandir a tabela: {e}")
                return

            # 3️⃣ Atualizar o campo com a OS do GSPN
            try:
                campo_os.clear()
                campo_os.send_keys(os_gspn)
                print(f"✅ Campo ASC_JOB_NO corrigido para: {os_gspn}")

                # Clicar em salvar
                driver.find_element(By.ID, "btnSave").click()
                print("💾 Salvando alterações...")

                # Aguardar recarregamento da página
                print("⏳ Aguardando a página recarregar (até 60s)...")
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.ID, "sbProductSummary"))
                )

                time.sleep(3)

                # Fechar popups após salvar
                fechar_popups(driver, timeout=5)
                esperar_popup(driver)
                time.sleep(2)
            except Exception as e:
                print(f"❌ Erro ao corrigir o campo ASC_JOB_NO: {e}")
                return

        else:
            print("✅ O ASC_JOB_NO já está correto. Prosseguindo...")

    except Exception as e:
        print(f"⚠️ Erro ao verificar o ASC_JOB_NO: {e}")

    except Exception as e:
        print(f"⚠️ Erro ao verificar o ASC_JOB_NO: {e}")




def muda_pra_ow(driver, os_gspn):
    """Inicia o processo de fechamento da OS no GSPN sem reparo."""

    print(f"\n🔄 Iniciando finalização da OS {os_gspn} sem reparo...")

    # 4️⃣ Capturar se a OS é LP ou OW
    try:
        span_produto = driver.find_element(By.ID, "sbProductSummary")
        # Pegar o texto visível dentro do <span>
        texto_produto = span_produto.text.strip()

        # Remover colchetes "[" e "]" e dividir pelo "//"
        dados = texto_produto.replace("[", "").replace("]", "").split("//")

        # O último valor será LP ou OW
        garantia_status = dados[-1].strip()
        print(f"📌 Status da OS: {garantia_status}")

    except Exception as e:
        print(f"❌ Erro ao capturar status da OS: {e}")
        return

    # 5️⃣ Se a OS for LP, aplicar VOID e atualizar para OW
    if garantia_status == "LP":
        print("🔄 OS está marcada como LP, aplicando VOID...")

        try:
            # Expandir a tabela "Informações do Produto"
            print("📂 Expandindo tabela 'Informações do Produto'...")
            driver.find_element(By.XPATH, "//tr[@onclick=\"javascript: initProductTab();\"]").click()
            if esperar_elemento_clicavel(driver, "//input[@id='wtyCheckBtn']", timeout=10):
                print("✅ Tabela 'Informações do Produto' expandida.")
            time.sleep(2)
            # Aplicar VOID
            select_void = driver.find_element(By.ID, "WTY_EXCEPTION")
            select_void.send_keys("VOID3")
            print("✅ VOID3 aplicado.")

            # Clicar no botão "Verificar Garantia"
            driver.find_element(By.ID, "wtyCheckBtn").click()
            print("🔄 Verificando garantia após VOID...")

            # Fechar popups que possam aparecer

            esperar_popup(driver)

            # Clicar em salvar
            driver.find_element(By.ID, "btnSave").click()
            print("💾 Salvando alterações...")
            time.sleep(2)
            # Fechar popups após salvar
            print('pré fechar popups')
            fechar_popups(driver)
            print('pós fechar popups')  # Agora fecha tanto popups do navegador quanto o popup interno
            esperar_popup(driver)

            # 6️⃣ Aguardar a página recarregar e verificar se agora a OS é OW
            print("⏳ Aguardando a página recarregar (até 60s)...")
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "sbProductSummary"))
            )
            time.sleep(3)  # Tempo extra para carregamento

            # Capturar novamente o status da OS
            span_produto = driver.find_element(By.ID, "sbProductSummary")
            
            # Pegar o texto visível dentro do <span>
            texto_produto = span_produto.text.strip()

            # Remover colchetes "[" e "]" e dividir pelo "//"
            dados = texto_produto.replace("[", "").replace("]", "").split("//")

            # O último valor será LP ou OW
            garantia_status = dados[-1].strip()
            if garantia_status == "OW":
                print("✅ OS agora está marcada como OW, podemos continuar o processo.")
            else:
                print(f"⚠️ OS ainda está como {garantia_status}, algo deu errado.")

        except Exception as e:
            print(f"❌ Erro ao aplicar VOID e verificar OW: {e}")
            return

    else:
        print("✅ OS já está marcada como OW, prosseguindo.")
        return True
    # Aqui continuaremos com os próximos passos do fechamento


def deletar_pecas(driver, os_gspn):
    """Deleta todas as peças cadastradas na OS do GSPN, incluindo cancelamento de G/I quando necessário."""
    print(f"🔄 Verificando peças inseridas na OS {os_gspn}...")

    try:
        # 1️⃣ Aguardar a tabela de peças carregar
        original_window = driver.current_window_handle
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "partsTableBody"))
        )

        while True:
            # 2️⃣ Obter a lista de peças (atualizado a cada iteração)
            pecas = driver.find_elements(By.XPATH, "//tbody[@id='partsTableBody']/tr")

            if not pecas:
                print("✅ Nenhuma peça encontrada na OS.")
                return

            print(f"🔍 {len(pecas)} peça(s) encontrada(s). Iniciando exclusão...")

            # 3️⃣ Processar cada peça de forma segura
            for _ in range(len(pecas)):  # Usa o tamanho original para evitar loops infinitos
                pecas = driver.find_elements(By.XPATH, "//tbody[@id='partsTableBody']/tr")  # Recoleta a lista atualizada
                if not pecas:
                    print("✅ Todas as peças foram removidas com sucesso.")
                    return

                peca = pecas[0]  # Sempre processa a primeira peça da lista
                try:
                    # Verificar se há botão "Cancelar G/I"
                    botao_cancelar_gi = peca.find_elements(By.XPATH, ".//input[@value='Cancelar G/I']")
                    if botao_cancelar_gi:
                        print("⚠️ Peça requer cancelamento de G/I antes da exclusão. Processando...")
                        botao_cancelar_gi[0].click()

                        # Aguardar até a nova janela ser aberta
                        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)

                        # Alternar para a nova janela
                        driver.switch_to.window(driver.window_handles[-1])
                        new_window = driver.current_window_handle

                        # Aguardar o botão "Cancelar G/I" dentro da nova janela
                        botao_confirmar_cancelamento = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//span[@id='buttonName']/a[contains(text(), 'Cancelar G/I')]"))
                        )
                        botao_confirmar_cancelamento.click()
                        print("✅ Cancelamento de G/I solicitado.")

                        # Aguardar o alerta e aceitá-lo
                        try:
                            esperar_popup(driver)
                        except: print('Voltanto pra janea original')
                        print("✅ Alerta de confirmação aceita.")

                        # Aguardar a nova janela fechar
                        while new_window in driver.window_handles:
                            time.sleep(0.5)  # Aguarda até que a janela desapareça

                        driver.switch_to.window(original_window)

                        # 4️⃣ Garantir que voltamos para a aba correta no GSPN
                        os_extraida = localizar_aba_gspn(driver)
                        if os_extraida != os_gspn:
                            aba_correta = False
                            for aba in driver.window_handles:
                                driver.switch_to.window(aba)
                                try:
                                    os_extraida = localizar_aba_gspn(driver)
                                    if os_extraida == os_gspn:
                                        print(f"✅ Aba correta confirmada: OS {os_extraida}")
                                        aba_correta = True
                                        break
                                except:
                                    continue
                            
                            if not aba_correta:
                                raise Exception(f"❌ Não foi possível encontrar a aba correta para a OS {os_gspn}.")

                        # 🟢 Agora aguardamos o botão "Agenda" ficar clicável antes de continuar
                        #WebDriverWait(driver, 15).until(
                         #   EC.element_to_be_clickable((By.ID, "tableScheduleBtn"))
                       # )
                        print("🔄 Página recarregada após cancelamento de G/I.")

                    # 5️⃣ Agora, localizar e clicar no botão de deletar a peça
                    botao_deletar = peca.find_elements(By.XPATH, ".//a[@name='partsDeleteBtn']")
                    if botao_deletar:
                        pecas_antes = len(driver.find_elements(By.XPATH, "//tbody[@id='partsTableBody']/tr"))

                        botao_deletar[0].click()
                        print("🗑️ Peça excluída.")

                        # Aguardar o alerta de confirmação e aceitá-lo
                        esperar_popup(driver)
                        print("✅ Confirmação de exclusão aceita.")

                        # 🟢 Agora aguardamos a atualização da quantidade de peças
                        WebDriverWait(driver, 15).until(
                            lambda d: len(d.find_elements(By.XPATH, "//tbody[@id='partsTableBody']/tr")) < pecas_antes
                        )

                        print("🔄 Página recarregada após exclusão da peça.")

                        # **Sair do loop e reavaliar a lista de peças**
                        break  

                except Exception as e:
                    print(f"⚠️ Erro ao processar peça: {e}")
                    continue  # Continua para a próxima peça

    except Exception as e:
        print(f"❌ Erro ao deletar peças da OS: {e}")




# Diretório onde os anexos estão localizados
CAMINHO_ANEXOS = r"C:\\Users\\Gestão MX\\Documents\\AutoMX\\Anexos"

# Arquivos e suas categorias no sistema
ANEXOS_OBRIGATORIOS = {
    "OFF FOTA.pdf": "ATT03",  # Official Document
    "SERIAL FOTA.pdf": "ATT02",  # Evidencia de Serial
    "SN LABEL FOTA.pdf": "ATT01"  # S/N Label
}

def verificar_e_anexar(driver):
    """Verifica os anexos da OS e anexa os que estiverem faltando."""

    print("🔍 Verificando anexos da OS...")

    try:
        # Salvar a aba original antes de abrir a nova janela
        original_window = driver.current_window_handle

        # 1️⃣ Verificar se a tabela de anexos está expandida, se não, expandir
        div_anexos = driver.find_element(By.ID, "divAttach")
        if "display: none;" in div_anexos.get_attribute("style"):
            print("📂 Expandindo tabela de anexos...")
            driver.find_element(By.XPATH, "//tr[@onclick=\"javascript: toggleTable('Attach');\"]").click()

            # Aguardar até que a tabela de anexos fique visível
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, "attachTable"))
            )
            print("✅ Tabela de anexos expandida e visível.")

        # 2️⃣ Obter a lista de anexos já cadastrados pela categoria
        anexos_existentes = set()
        anexos_tabela = driver.find_elements(By.XPATH, "//tbody[@id='attachTableBody']/tr/td/input[@name='docTypeCode']")

        for anexo in anexos_tabela:
            categoria = anexo.get_attribute("value")  # Pega o código da categoria (ex: ATT03)
            anexos_existentes.add(categoria)

        print(f"📌 Categorias de anexos já presentes: {anexos_existentes}")

        # 3️⃣ Verificar quais anexos estão faltando com base nas categorias
        anexos_faltando = {
            arquivo: tipo for arquivo, tipo in ANEXOS_OBRIGATORIOS.items() if tipo not in anexos_existentes
        }

        if not anexos_faltando:
            print("✅ Todos os anexos obrigatórios já estão presentes.")
            return

        print(f"⚠️ Faltam os seguintes anexos: {list(anexos_faltando.keys())}")

        # 4️⃣ Abrir janela de upload
        print("📂 Abrindo janela de upload...")
        driver.find_element(By.XPATH, "//table[@id='btnInsertAttach']//a[contains(text(), 'Insert(Multi)')]").click()

        # 5️⃣ Aguardar nova janela e alternar para ela
        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
        driver.switch_to.window(driver.window_handles[-1])
        new_window = driver.current_window_handle
        print("✅ Janela de upload aberta.")

        # 6️⃣ Enviar todos os arquivos e esperar a tabela atualizar antes de seguir
        for arquivo, categoria in anexos_faltando.items():
            caminho_arquivo = os.path.join(CAMINHO_ANEXOS, arquivo)

            if not os.path.exists(caminho_arquivo):
                print(f"❌ Arquivo não encontrado: {caminho_arquivo}")
                continue

            print(f"📤 Anexando arquivo: {arquivo} ({categoria})")
            upload_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "uploadFile"))
            )
            upload_input.send_keys(caminho_arquivo)
            time.sleep(0.5)

            # 🔄 Aguardar até que o novo arquivo apareça na tabela antes de prosseguir
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.XPATH, "//tbody[@id='attachTableBody']/tr")) > len(anexos_existentes)
            )

            print(f"✅ Arquivo {arquivo} adicionado à lista de anexos.")

        print("✅ Todos os arquivos foram selecionados.")

        # 7️⃣ Obter a lista de anexos na tabela para garantir que cada um tem seu seletor correto
        anexos_tabela_upload = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//tbody[@id='attachTableBody']/tr"))
        )

        if len(anexos_tabela_upload) != len(anexos_faltando):
            raise Exception("❌ A quantidade de arquivos anexados não corresponde à esperada.")

        # 8️⃣ Selecionar categorias para os arquivos enviados
        for i, (arquivo, categoria) in enumerate(anexos_faltando.items()):
            try:
                # Localizar a linha correta na tabela
                linha = anexos_tabela_upload[i]

                # Localizar a lista suspensa dentro da linha correta
                seletor_categoria = linha.find_element(By.XPATH, ".//select[@id='IV_DESC']")

                # 8.1️⃣ Clicar para expandir a lista
                seletor_categoria.click()
                WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//select[@id='IV_DESC']/option[@value='{categoria}']"))
                )

                # 8.2️⃣ Selecionar a opção correta
                select = Select(seletor_categoria)
                select.select_by_value(categoria)

                # 8.3️⃣ Aguarde até que a categoria seja realmente selecionada
                WebDriverWait(driver, 5).until(
                    lambda d: seletor_categoria.get_attribute("value") == categoria
                )

                print(f"✅ Categoria selecionada para {arquivo}: {categoria}")

                # 8.4️⃣ Clicar em um espaço vazio da página para garantir que a lista seja fechada
                driver.find_element(By.TAG_NAME, "body").click()
                time.sleep(0.5)  # Pequeno delay para confirmar que a lista foi fechada

            except Exception as e:
                print(f"❌ Erro ao selecionar categoria para {arquivo}: {e}")

        print("✅ Todas as categorias foram selecionadas corretamente.")

        # 9️⃣ Pequeno delay antes de clicar no botão "Anexar" (garante que tudo esteja pronto)
        time.sleep(1)

        # 🔟 Clicar no botão "Anexar"
        driver.find_element(By.XPATH, "//form[@id='attachForm']//a[contains(text(), 'Anexar')]").click()
        print("📤 Enviando anexos...")

        # 🔄 Aguardar a nova janela fechar automaticamente
        while new_window in driver.window_handles:
            time.sleep(0.5)  # Aguarda até que a janela desapareça

        # 🔄 Voltar para a aba original no GSPN
        driver.switch_to.window(original_window)

        # 🔄 Aguardar a página principal recarregar com os novos anexos
        WebDriverWait(driver, 10).until(
            lambda d: len(d.find_elements(By.XPATH, "//tbody[@id='attachTableBody']/tr")) > len(anexos_existentes)
        )

        print("✅ Página recarregada e anexos verificados.")

    except Exception as e:
        print(f"❌ Erro ao verificar/anexar documentos: {e}")

def finalizar_remontagem_ow(driver, os_gspn):
    """Finaliza a OS GSPN como remontagem e muda o status para reparo completo."""

    print(f"🔄 Iniciando finalização da OS {os_gspn} como 'Remontagem OW'...")

    try:
       # 1️⃣ Garantir que a OS está como OW
        muda_pra_ow(driver, os_gspn)
        time.sleep(2)
        """# 2️⃣ Deletar peças associadas à OS
        deletar_pecas(driver, os_gspn)

        # 3️⃣ Verificar e anexar documentos
        verificar_e_anexar(driver, os_gspn)"""

        # 1️⃣ Alterar status para "Reparo completo"
        print("🔄 Alterando status para 'Reparo completo'...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "STATUS"))
        )
        select_status = Select(driver.find_element(By.ID, "STATUS"))
        select_status.select_by_visible_text("Reparo completo")
        time.sleep(1)
        print("🔄 Alterando Reason para 'Reparo finalizado[HL005]'...")
        #WebDriverWait(driver, 10).until(
        #    EC.presence_of_element_located((By.ID, "REASON"))
        #)
        #print('passou')
        dropdown_reason = driver.find_element(By.ID, "REASON")
        dropdown_reason.click()
        select_reason = Select(driver.find_element(By.ID, "REASON"))
        select_reason.select_by_visible_text("Reparo finalizado[HL005]")

        # 3️⃣ Clicar no botão do relógio
        print("🔄 Atualizando data/hora com o botão relógio...")
        #WebDriverWait(driver, 10).until(
        #    EC.element_to_be_clickable((By.XPATH, "//input[@id='tableScheduleBtn']"))
        #)
        #driver.find_element(By.XPATH, "//input[@id='tableScheduleBtn']").click()
        time.sleep(1)

        # 4️⃣ Preencher campo de descrição do reparo
        print("🔄 Preenchendo campo de descrição do reparo com 'REMONTAGEM'...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "REPAIR_DESC"))
        )
        campo_descricao = driver.find_element(By.ID, "REPAIR_DESC")
        campo_descricao.clear()
        campo_descricao.send_keys("REMONTAGEM")

        # 5️⃣ Selecionar "Troca de Acessório" no select "LAB_TYPE"
        print("🔄 Selecionando 'Troca de Acessório' no campo LAB_TYPE...")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "LAB_TYPE"))
        )
        select_lab_type = Select(driver.find_element(By.ID, "LAB_TYPE"))
        select_lab_type.select_by_visible_text("Troca de Acessório")

        # 6️⃣ Selecionar valores na tr id="IrisCodeDec"
        print("🔄 Selecionando IRIS_CONDI, IRIS_SYMPT_QCODE e IRIS_SYMPT...")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IRIS_CONDI"))
        )
        select_iris_condi = Select(driver.find_element(By.ID, "IRIS_CONDI"))
        select_iris_condi.select_by_visible_text("1-Defeito")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IRIS_SYMPT_QCODE"))
        )
        select_iris_sympt_qcode = Select(driver.find_element(By.ID, "IRIS_SYMPT_QCODE"))
        select_iris_sympt_qcode.select_by_visible_text("SRC012-Problema de Alimentação")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IRIS_SYMPT"))
        )
        select_iris_sympt = Select(driver.find_element(By.ID, "IRIS_SYMPT"))
        select_iris_sympt.select_by_visible_text("T12-Não liga")

        # 7️⃣ Selecionar valores na tr id="defectCodeTr"
        print("🔄 Selecionando IRIS_REPAIR_QCODE e IRIS_REPAIR...")
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IRIS_REPAIR_QCODE"))
        )
        select_iris_repair_qcode = Select(driver.find_element(By.ID, "IRIS_REPAIR_QCODE"))
        select_iris_repair_qcode.select_by_visible_text("SRC005-Remontagem/Reconexão")

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "IRIS_REPAIR"))
        )
        select_iris_repair = Select(driver.find_element(By.ID, "IRIS_REPAIR"))
        select_iris_repair.select_by_visible_text("M11-Re-montagem")
        #print('localizando relogio')
        #botao_relogio = WebDriverWait(driver, 10).until(
        #EC.element_to_be_clickable((By.XPATH, "//div[@id='divRepair']//td[@id='serviceDateTD2_LAST_APP']//img[@src='/img/ico_time.gif']")))
        try:
            botao_relogio = driver.find_element(By.XPATH, "//div[@id='divRepair']//td[@id='serviceDateTD2']//img[@src='/img/ico_time.gif']")
        except: print('Botão relógio indisponível.')
        print('click no relogio')
        time.sleep(1)
        botao_relogio.click()
        time.sleep(1)
        # 8️⃣ Clicar no botão Salvar
        print("💾 Salvando alterações...")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@id='divButtons']//input[@id='btnSave']"))
        )
        driver.find_element(By.XPATH, "//div[@id='divButtons']//input[@id='btnSave']").click()
        
        time.sleep(5)

        # 9️⃣ Fechar popups
        print("🔄 Fechando popups após salvar...")
        esperar_popup(driver)
        fechar_popups(driver)
        esperar_popup(driver)  # Chamar a função que fecha popups
        try:
            feedback_popup = driver.find_element(By.ID, "divFeedbackInfo")
            if feedback_popup.is_displayed():
                print("⚠️ Popup de feedback de peças detectado! Abrindo OS novamente...")
                abrir_os.abrir_os_gpn(driver, os_gspn)
            else:
                print("✅ Nenhum popup adicional visível.")
        except:
            print("✅ Nenhum popup adicional detectado.")
    
    except Exception as e:
        print(f"❌ Erro ao finalizar remontagem OW da OS {os_gspn}: {e}")


def entregue_sem_reparo(driver, os_gspn):
    """Finaliza a OS do GSPN como 'Produto Entregue', garantindo que está OW e sem peças."""

    print(f"🚚 Iniciando entrega sem reparo da OS {os_gspn}...")

    # 1️⃣ Verificar se a OS está OW
    try:
        span_produto = driver.find_element(By.ID, "sbProductSummary")
        texto_produto = span_produto.text.strip()
        dados = texto_produto.replace("[", "").replace("]", "").split("//")
        garantia_status = dados[-1].strip()
        print(f"📌 Status da OS: {garantia_status}")
    except Exception as e:
        print(f"❌ Erro ao capturar status da OS: {e}")
        return

    if 'LP' in garantia_status:
        raise Exception(f"❌ A OS {os_gspn} está LP! Não pode ser entregue.")

    print("✅ OS está OW, prosseguindo...")

    # 2️⃣ Verificar se há peças na OS
    try:
        pecas_tabela = driver.find_elements(By.XPATH, "//tbody[@id='partsTableBody']/tr")
        if len(pecas_tabela) > 0:
            raise Exception(f"❌ Existem peças na OS {os_gspn}! Remova antes de finalizar.")
    except Exception:
        print("✅ Nenhuma peça na OS. Prosseguindo...")

    # 3️⃣ Alterar status para "Produto Entregue"
    print("🔄 Alterando status para 'Produto Entregue'...")
    select_status = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "STATUS"))
    )
    select_status.send_keys("Produto Entregue")
    time.sleep(1)

    # 4️⃣ Clicar no botão Relógio para preencher a data/hora
    print("⏳ Atualizando data/hora...")
    botao_relogio = driver.find_element(By.XPATH, "//div[@id='divRepair']//td[@id='serviceDateTD2']//img[@src='/img/ico_time.gif']")
    botao_relogio.click()
    time.sleep(1)

    # 5️⃣ Clicar no botão Salvar
    print("💾 Salvando alterações...")
    botao_salvar = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//div[@id='divButtons']//input[@id='btnSave']"))
    )
    botao_salvar.click()
    time.sleep(8)
    
    # 6️⃣ Fechar popup com tratamento de erro
    try:
        esperar_popup(driver)
        fechar_popups(driver)
        time.sleep(5)
        esperar_popup(driver)
        print(f"✅ OS {os_gspn} finalizada como 'Produto Entregue' com sucesso!")
    except Exception as e:
        if "Nenhum popup foi detectado" in str(e):
            print("⚠️ Nenhum popup foi detectado. Verificando status na página...")
            driver.refresh()
            time.sleep(5)
            
            try:
                status_select = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='divRepair']//select[@id='STATUS']"))
                )
                selected_option = status_select.find_element(By.XPATH, "./option[@selected]").text.strip()
                if selected_option == "Produto Entregue":
                    print(f"✅ OS {os_gspn} finalizada corretamente apesar da ausência do popup.")
                else:
                    raise Exception(f"❌ O status da OS {os_gspn} não foi atualizado corretamente!")
            except Exception as e:
                print(f"❌ Erro ao verificar o status após atualização: {e}")
        else:
            raise e

def finalizar_p_reabrir(driver, os_gspn):
    print("Iniciando finalização completa para reabertura.")
    abrir_os.abrir_os_gspn(driver, os_gspn)
    time.sleep(3)
    confere_asc_job(driver, os_gspn)
    time.sleep(2)
    m=0
    while m < 2:
        try:
            muda_pra_ow(driver, os_gspn)

            m +=2
        except: 
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
            abrir_os(driver, os_gspn)
            time.sleep(3)
            m +=1
            print('Não foi possível mudar pra OW.')

    time.sleep(2)
    deletar_pecas(driver, os_gspn)
    time.sleep(1)
    verificar_e_anexar(driver)
    time.sleep(2)
    f = 0
    while f < 2:
        try:
            finalizar_remontagem_ow(driver, os_gspn)
            "Passou da finalização"
            break

            
        except:
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
            abrir_os(driver, os_gspn)
            time.sleep(3)
            f +=1
            print('Erro para finalizar OW')
    time.sleep(2)
    e = 0
    while e < 2:
        try:
            entregue_sem_reparo(driver, os_gspn)
            esperar_popup(timeout=3)
            print('Passou do produto entregue')
            e +=2
            break
        except:
            driver.close()
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(3)
            abrir_os(driver, os_gspn)
            time.sleep(2)
            try:
                status_select = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='divRepair']//select[@id='STATUS']"))
                )
                selected_option = status_select.find_element(By.XPATH, "./option[@selected]").text.strip()
                if selected_option == "Produto Entregue":
                    print(f"✅ OS {os_gspn} finalizada corretamente apesar do erro.")
                else:
                    raise Exception(f"❌ O status da OS {os_gspn} não foi atualizado corretamente!")
            except Exception as e:
                print(f"❌ Erro ao verificar o status após atualização: {e}")
            e += 2

    time.sleep(2)
    driver.close()
    #time.sleep(1)
    driver.switch_to.window(driver.window_handles[-1])
    auto_cos.deletar_cos(os_gspn)