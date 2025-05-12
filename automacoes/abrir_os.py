from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def abrir_os_cos(driver, os_numero):
    """Abre a OS do COS em uma nova aba e aguarda a aba estar disponível."""
    driver.switch_to.window(driver.window_handles[-1])
    url_cos = f"http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?NumeroOSBusca={os_numero}"
    abas_antes = set(driver.window_handles)  # Captura abas antes da nova abrir

    driver.execute_script(f"window.open('{url_cos}', '_blank');")

    # Aguarda a nova aba ser aberta
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(abas_antes))

    # Muda para a nova aba (última aberta)
    driver.switch_to.window(driver.window_handles[-1])

def abrir_os_gspn(driver, os_numero):
    driver.switch_to.window(driver.window_handles[-1])
    """Abre a OS do GSPN em uma nova aba e aguarda a aba estar disponível."""
    print('Abrindo OS GSPN')

    abas_antes = set(driver.window_handles)  # Captura abas antes da nova abrir

    url_gspn = f"https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID={os_numero}#tabInfoHref"
    driver.execute_script(f"window.open('{url_gspn}', '_blank');")

    # Aguarda a nova aba ser aberta
    WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > len(abas_antes))

    # Muda para a nova aba (última aberta)
    driver.switch_to.window(driver.window_handles[-1])

