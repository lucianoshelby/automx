import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta, timezone
from coletar_dados import fetch_os_data

data_atual = datetime.now().strftime('%Y%m%d')
hora_gmt0 = datetime.now(timezone(timedelta(hours=-3))).strftime('%H%M%S')
def montar_payload(object_id):
    """
    Monta o payload para a requisição HTTP mantendo a ordem dos campos
    e inserindo dinamicamente as informações de peças
    
    Args:
        html_content: HTML da página
        pecas: Lista de dicionários com informações das peças (PARTS_CODE, PARTS_QTY)
        warning_skip: Flag para ignorar avisos
        object_id: ID do objeto para buscar dados SAW
        cookies: Cookies para autenticação
        
    Returns:
        OrderedDict com o payload completo
    """
    dados_full = fetch_os_data(object_id)
    html_content = dados_full['html_os']
    cookies = dados_full['cookies']
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Data e hora atuais

    
    # Definimos a ordem exata dos campos conforme a requisição original
    # Usamos uma lista de tuplas para manter a ordem e permitir campos repetidos
    payload_fields = [
        ("ONLY_WTY_CREATE", ""),
        ("VERIFY_FLAG", ""),
        ("WARNING_SKIP", "X"),
        ("OLD_PARTS_SERIAL_FLAG", "X"),
        ("VERIFY_INITIAL", "N"),
        ("RENT_DT", ""),
        ("OPERATOR", ""),
        ("AUTO_DO", ""),
        ("SUB_SVC_TYPE_AD", ""),
        ("VIEW_PAGE_ONLY", "false"),
        ("btnWARRequest", "Solicitação de Exceção de Garantia"),
        ("btnSawRequest", "SAW Request"),
        ("btnSendDocument", "Enviar Documento"),
        ("ASC_JOB_NO", extract_js_variable(soup, "_l.ASC_JOB_NO")) or '',
        ("ASSIGNED_ASC_CODE", ""),
        ("ASC_CODE", extract_js_variable(soup, "_l.ASC_CODE") or "0002446971"),
        ("B2B_SVC", ""),
        ("DATA_ORIGIN_CODE", "I"),
        ("DATA_ORIGIN", "From ASC"),
        ("CC_CODE", ""),
        ("CC_CODE_BEFORE", ""),
        ("DEALER_JOB_NO", soup.find('input', {'id': 'DEALER_JOB_NO'}).get('value', '') if soup.find('input', {'id': 'DEALER_JOB_NO'}) else ""),
        ("OBJECT_ID", extract_js_variable(soup, "_l.ObjectId")),
        ("CREATE_DATE", soup.find("div", id="divGeneral").find("input", {"id": "CREATE_DATE"}).get("value", "")),
        ("ALT_TEL_NO", ""),
        ("NAME_FIRST", extract_js_variable(soup, "_l.NAME_FIRST")),
        ("NAME_LAST", extract_js_variable(soup, "_l.NAME_LAST")),
        ("HOMEPHON_NUMBER", extract_js_variable(soup, "_l.HOME_PHONE")),
        ("MOBILE_NUMBER", extract_js_variable(soup, "_l.mobile_phone")),
        ("OFFICEPHON_NUM", soup.find("input", {"id": "OFFICEPHON_NUM"}).get("value", "")),
        ("STREET", extract_js_variable(soup, "_l.bpStreet1")),
        ("CITY", extract_js_variable(soup, "_l.bpCity")),
        ("REGION", extract_js_variable(soup, "_l.bpRegionCode")),
        ("POST_CODE", extract_js_variable(soup, "_l.bpPostCode")),
        ("EMAIL", soup.find("div", id="divCustomer").find("input", {"id": "EMAIL"}).get("value", "")),
        ("CONSUMER", extract_js_variable(soup, "_l.CONSUMER")),
        ("CONTACT_FLAG", soup.find("div", id="divCustomer").find("input", {"id": "CONTACT_FLAG"}).get("value", "")),
        ("MODEL", extract_js_variable(soup, "_l.MODEL")),
        ("MODEL_NAME", soup.find("div", id="divProduct").find("input", {"id": "MODEL_NAME", "type": "hidden"}).get("value", "")),
        ("CIC_PRCD", extract_js_variable(soup, "_l.CIC_PRCD")),
        ("LOC_PRCD", extract_js_variable(soup, "_l.LOC_PRCD")),
        ("SVC_PRCD", extract_js_variable(soup, "_l.SVC_PRCD")),
        ("SERIAL_NO", extract_js_variable(soup, "_l.SERIAL_NO")),
        ("IMEI", extract_js_variable(soup, "_l.IMEI")),
        ("PRODUCT_DATE", extract_js_variable(soup, "_l.PRODUCT_DATE")),
        ("PURCHASE_DATE", extract_js_variable(soup, "_l.PURCHASE_DATE")),
        ("IN_OUT_WTY", extract_js_variable(soup, "_l.IN_OUT_WTY")),
        ("PURCHASE_PLACE", ""),
        ("LOCAL_INVOICE_NO", ""),
        ("ACCESSORY", extract_js_variable(soup, "_l.ACCESSORY") or "SEM ACESSORIOS"),
        ("WTY_EXCEPTION", extract_js_variable(soup, "_l.WTY_EXCEPTION")),
        ("DEALER", soup.find("div", id="divProduct").find("input", {"id": "DEALER"}).get("value", "")),
        ("PRINTED_PAGE", extract_js_variable(soup, "_l.PRINTED_PAGE") or "0"),
        ("EWTY_FLAG", extract_js_variable(soup, "_l.EWTY_FLAG") or ""),
        ("DISPLAY_UNIT", extract_js_variable(soup, "_l.DISPLAY_UNIT") or ""),
        ("AUTH_GR", extract_js_variable(soup, "_l.AUTH_GR")),
        ("HQ_SVC_PRCD", extract_js_variable(soup, "_l.hqSvcProd")),
        ("ADH_FLAG", extract_js_variable(soup, "_l.ADH_FLAG") or ""),
        ("CERTI_NO", extract_js_variable(soup, "_l.CERTI_NO")),
        ("DAMAGE_EXPLANATION", extract_js_variable(soup, "_l.damageExplanation") or ""),
        ("LOSS_TYPE_ID", extract_js_variable(soup, "_l.lossTypeId") or ""),
        ("CLAIM_INSU_NO", extract_js_variable(soup, "_l.claimInsuNo") or ""),
        ("POLICY_ID", extract_js_variable(soup, "_l.policyId") or ""),
        ("PACK_BASE", extract_js_variable(soup, "_l.PACK_BASE") or "M"),
        ("CHARGE_TYPE", extract_js_variable(soup, "_l.chargeType") or ""),
        ("CHARGE_AMOUNT", extract_js_variable(soup, "_l.chargeAmount") or "0.00"),
        ("CHARGE_WAERS", extract_js_variable(soup, "_l.chargeWaers") or ""),
        ("rType", extract_js_variable(soup, "_l.rType") or ""),
        ("sCompany", extract_js_variable(soup, "_l.sCompany") or ""),
        ("eppType", soup.find("div", id="divProduct").find("input", {"id": "eppType"}).get("value", "")),
        ("eppSymptom", soup.find("div", id="divProduct").find("input", {"id": "eppSymptom"}).get("value", "")),
        ("eppContractNo", soup.find("div", id="divProduct").find("input", {"id": "eppContractNo"}).get("value", "")),
        ("MODULE_ID", soup.find("div", id="divProduct").find("input", {"id": "MODULE_ID"}).get("value", "")),
        ("CARRIER", extract_js_variable(soup, "_l.CARRIER") or "C999"),
        ("SALES_BUYER", soup.find("div", id="divProduct").find("input", {"id": "SALES_BUYER"}).get("value", "")),
        ("SALES_COUNTRY", soup.find("div", id="divProduct").find("input", {"id": "SALES_COUNTRY"}).get("value", "")),
        ("SERVICE_TYPE", extract_js_variable(soup, "_l.SERVICE_TYPE")),
        ("ENGINEER", extract_js_variable(soup, "_l.ENGINEER")),
        ("sENGINEER", extract_js_variable(soup, "_l.ENGINEER")),
        ("ESCAL_ASC", ""),
        ("STATUS", extract_js_variable(soup, "_l.CurrStatus")),
        ("REASON", extract_js_variable(soup, "_l.REASON")),
        ("SERVICE_DATE", extract_js_variable(soup, "_l.REPAIR_COMP_DATE") or "00/00/0000"),
        ("SERVICE_TIME", extract_js_variable(soup, "_l.REPAIR_COMP_TIME") or "00:00:00"),
        ("FIRST_APP_DATE_DY_STT", soup.find("input", {"id": "FIRST_APP_DATE_DY_STT"}).get("value", "")),
        ("FIRST_APP_TIME_DY_STT", soup.find("input", {"id": "FIRST_APP_TIME_DY_STT"}).get("value", "")),
        ("LAST_APP_DATE_DY_STT", soup.find("input", {"id": "LAST_APP_DATE_DY_STT"}).get("value", "")),
        ("LAST_APP_TIME_DY_STT", soup.find("input", {"id": "LAST_APP_TIME_DY_STT"}).get("value", "")),
        ("FIRST_VISIT_DATE_DY_STT", extract_js_variable(soup, "_l.FIRST_VISIT_DATE") or ""),
        ("FIRST_VISIT_TIME_DY_STT", ""),
        ("LAST_VISIT_DATE_DY_STT", extract_js_variable(soup, "_l.LAST_VISIT_DATE") or "00/00/0000"),
        ("LAST_VISIT_TIME_DY_STT", extract_js_variable(soup, "_l.LAST_VISIT_TIME") or "00:00:00"),
        ("STATUS_COMMENT", ""),
        ("REMARK", extract_js_variable(soup, "_l.REMARK")),
        ("DEFECT_DESC", extract_js_variable(soup, "_l.DEFECT_DESC")),
        ("DEFECTDESC_L", soup.find("textarea", {"id": "DEFECTDESC_L"}).text if soup.find("textarea", {"id": "DEFECTDESC_L"}) else ""),
        ("REPAIR_DESC", extract_js_variable(soup, "_l.REPAIR_DESC") or ""),
        ("LAB_TYPE", extract_js_variable(soup, "_l.LAB_TYPE")),
        ("DEF_BLK", extract_js_variable(soup, "_l.DEF_BLK") or ""),
        ("IRIS_CONDI", extract_js_variable(soup, "_l.IRIS_CONDI")),
        ("IRIS_SYMPT_QCODE", soup.find("input", {"id": "SAVED_IRIS_SYMPT_QCODE"}).get("value", "")),
        ("SAVED_IRIS_SYMPT_QCODE", soup.find("input", {"id": "SAVED_IRIS_SYMPT_QCODE"}).get("value", "")),
        ("IRIS_SYMPT", extract_js_variable(soup, "_l.IRIS_SYMPT")),
        ("IRIS_DEFECT_QCODE", soup.find("input", {"id": "SAVED_IRIS_DEFECT_QCODE"}).get("value", "")),
        ("SAVED_IRIS_DEFECT_QCODE", soup.find("input", {"id": "SAVED_IRIS_DEFECT_QCODE"}).get("value", "")),
        ("IRIS_DEFECT", extract_js_variable(soup, "_l.IRIS_DEFEC")),
        ("IRIS_REPAIR_QCODE", soup.find("input", {"id": "SAVED_IRIS_REPAIR_QCODE"}).get("value", "")),
        ("SAVED_IRIS_REPAIR_QCODE", soup.find("input", {"id": "SAVED_IRIS_REPAIR_QCODE"}).get("value", "")),
        ("IRIS_REPAIR", soup.find('select', {'id': 'IRIS_REPAIR'}).find('option', selected=True)['value'] if soup.find('select', {'id': 'IRIS_REPAIR'}).find('option', selected=True) else ""),
        ("REP_TYPE", extract_js_variable(soup, "_l.REP_TYPE")),
        ("SVC_INDICATOR", extract_js_variable(soup, "_l.SVC_INDICATOR") or ""),
        ("QNA_CODE", soup.find("input", {"id": "QNA_CODE"}).get("value", "")),
        ("GAS_CHARGE", extract_js_variable(soup, "_l.GAS_CHARGE") or ""),
        ("DISTANCE", soup.find("input", {"id": "DISTANCE"}).get("value", "")),
        ("orig_distance_in", soup.find("input", {"id": "orig_distance_in"}).get("value", "")),
        ("VANID", ""),
        ("TECH_ID", ""),
        ("TECH_ID_DESC", ""),
    ]

    def extract_parts_data():
        # Criar objeto BeautifulSoup com o HTML
        soup = BeautifulSoup(dados_full['html_os'], 'html.parser')
        
        # Lista para armazenar todos os payloads
        
        
        # Tentar encontrar o tbody da tabela de peças
        parts_table_body = soup.select_one('#partsTableBody')
        
        # Verificar se a tabela existe e tem linhas
        if not parts_table_body or not parts_table_body.find_all('tr'):
            return print("Não há peças na OS")
        
        # Encontrar todas as linhas da tabela de peças
        parts_rows = parts_table_body.find_all('tr')
        
        # Para cada linha (peça) na tabela
        for row in parts_rows:
            # Bloco de payload para cada peça
            part_payload = [
                ("PARTS_SEQ_NO", row.find("input", {"id": "PARTS_SEQ_NO"}).get("value", "")),
                ("SHIP_DATE", row.find("input", {"id": "SHIP_DATE"}).get("value", "")),
                ("OLD_PARTS_SEQ_NO", row.find("input", {"id": "OLD_PARTS_SEQ_NO"}).get("value", "")),
                ("OLD_SHIP_DATE", row.find("input", {"id": "OLD_SHIP_DATE"}).get("value", "")),
                ("REPAIR_LOC", row.find("input", {"id": "REPAIR_LOC"}).get("value", "")),
                ("PROACTIVE_FLAG", row.find("input", {"id": "PROACTIVE_FLAG"}).get("value", "")),
                ("PARTS_STATUS", row.find("input", {"id": "PARTS_STATUS"}).get("value", "P")),
                ("ORG_PARTS_CODE", row.find("input", {"id": "ORG_PARTS_CODE"}).get("value", "")),
                ("PARTS_CODE", row.find("input", {"id": "PARTS_CODE"}).get("value", "")),
                ("PARTS_DESC", row.find("input", {"id": "PARTS_DESC"}).get("value", "")),
                ("INVOICE_NO", row.find("input", {"id": "INVOICE_NO"}).get("value", "")),
                ("INVOICE_ITEM_NO", row.find("input", {"id": "INVOICE_ITEM_NO"}).get("value", "")),
                ("PARTS_QTY", row.find("input", {"id": "PARTS_QTY"}).get("value", "")),
                ("D_REQUEST_NO", row.find("input", {"id": "D_REQUEST_NO"}).get("value", "")),
                ("REQUEST_NO", row.find("input", {"id": "REQUEST_NO"}).get("value", "")),
                ("REQUEST_ITEM_NO", row.find("input", {"id": "REQUEST_ITEM_NO"}).get("value", "")),
                ("PO_NO", row.find("input", {"id": "PO_NO"}).get("value", "")),
                ("SO_NO", row.find("input", {"id": "SO_NO"}).get("value", "")),
                ("SO_ITEM_NO", row.find("input", {"id": "SO_ITEM_NO"}).get("value", "")),
                ("D_SO_NO", row.find("input", {"id": "D_SO_NO"}).get("value", "")),
                ("OLD_SERIAL_MAT", row.find("input", {"id": "OLD_SERIAL_MAT"}).get("value", "")),
                ("SERIAL_MAT", row.find("input", {"id": "SERIAL_MAT"}).get("value", "")),
                ("OLD_FAB_ID", row.find("input", {"id": "OLD_FAB_ID"}).get("value", "")),
                ("FAB_ID", row.find("input", {"id": "FAB_ID"}).get("value", "")),
                ("PARTS_INOUT", row.find("input", {"id": "PARTS_INOUT"}).get("value", "")),
                ("GI_DATE", row.find("input", {"id": "GI_DATE"}).get("value", "")),
                ("gi_document_no", row.find("input", {"id": "gi_document_no"}).get("value", ""))
            ]
            payload_fields.extend(part_payload)
    extract_parts_data()
    # Campos de anexos
    def extract_attachments(soup):
        attachments = []
        attach_table = soup.find('tbody', id='attachTableBody')
        if attach_table:
            for row in attach_table.find_all('tr'):
                cells = row.find_all('td', class_='td_ac')
                if len(cells) >= 4:
                    doc_type = row.find('input', {'name': 'docTypeCode'})
                    file_name = row.find('input', {'name': 'file_name_org'})
                    if doc_type and file_name:
                        attachments.append({
                            'docTypeCode': doc_type.get('value', ''),
                            'file_name_org': file_name.get('value', '')
                        })
        return attachments or [{'docTypeCode': '', 'file_name_org': ''}]

    attachments = extract_attachments(soup)
    for attachment in attachments:
        payload_fields.extend([
            ("docTypeCode", attachment['docTypeCode']),
            ("file_name_org", attachment['file_name_org']),
        ])

    # Campos adicionais após anexos
    payload_fields.extend([
        ("attach_doc_type", "ATT01"),
        ("attach_doc_type_ewp", "ATT04"),
        ("SYMPTOM_CAT1", extract_js_variable(soup, "_l.SYMPTOM1_CODE") or "L2"),
        ("SYMPTOM_CAT2", extract_js_variable(soup, "_l.SYMPTOM2_CODE") or "01"),
        ("SYMPTOM_CAT3", extract_js_variable(soup, "_l.SYMPTOM3_CODE") or "01"),
        ("IV_FEEDBACK", soup.find('textarea', {'id': 'IV_FEEDBACK'}).text if soup.find('textarea', {'id': 'IV_FEEDBACK'}) else ""),
        ("CURR_STATUS", extract_js_variable(soup, "_l.CurrStatus")),
        ("CURR_STATUS_NAME", extract_js_variable(soup, "_l.CurrStatusDesc") or ""),
        ("CURR_REASON", extract_js_variable(soup, "_l.CurrReason") or ""),
        ("SUB_SVC_TYPE", ""),
        ("SUB_SVC_TYPE2", ""),
        ("SUB_SVC_TYPE3", extract_js_variable(soup, "_l.SUB_SVC_TYPE") or ""),
        ("REF_REMARK", ""),
        ("assignedFe", extract_js_variable(soup, "_l.ASC_CODE") or "0002446971"),
    ])

    # Campos SAW
    saw_fields = []
    if object_id and cookies:
        saw_fields = obter_dados_saw(object_id, cookies)
    for saw_status, saw_category in saw_fields:
        if saw_status[1] and saw_category[1]:
            payload_fields.append(saw_status)
            payload_fields.append(saw_category)

    # Campos de tentativa de chamada e datas
    payload_fields.extend([
        ("CALL_ATTEMPT1_DT", ""),
        ("CALL_ATTEMPT1_TM", ""),
        ("CALL_ATTEMPT2_DT", ""),
        ("CALL_ATTEMPT2_TM", ""),
        ("CALL_ATTEMPT3_DT", ""),
        ("CALL_ATTEMPT3_TM", ""),
        ("NEW_FIRMWARE", ""),
        ("UNIT_LOC", ""),
        ("TOKEN_NO", extract_js_variable(soup, "_l.TOKEN_NO") or extract_js_variable(soup, "_l.ObjectId")),
        ("NEW_MODEL", extract_js_variable(soup, "_l.NEW_MODEL") or ""),
        ("NEW_SERIAL_NO", extract_js_variable(soup, "_l.NEW_SERIAL_NO") or ""),
        ("NEW_IMEI_TXT", ""),
        ("NEW_IMEI", extract_js_variable(soup, "_l.NEW_IMEI") or ""),
        ("SHIP_METHOD", ""),
        ("CALL_RCV_DT", extract_js_variable(soup, "_l.CALL_RCV_DT") or "00/00/0000"),
        ("CALL_RCV_TM", soup.find("input", {"id": "CALL_RCV_TM"}).get("value", "")),
        ("ASC_ASSIGN_DATE", extract_js_variable(soup, "_l.ASC_ASSIGN_DATE")),
        ("ASC_ASSIGN_TIME", soup.find("input", {"id": "ASC_ASSIGN_TIME"}).get("value", "00:00:00")),
        ("ASC_ACK_DATE", soup.find("input", {"id": "ASC_ACK_DATE"}).get("value", "00/00/0000")),
        ("ASC_ACK_TIME", soup.find("input", {"id": "ASC_ACK_TIME"}).get("value", "00:00:00")),
        ("GOODS_DEL_DATE", soup.find("input", {"id": "GOODS_DEL_DATE"}).get("value", "00/00/0000")),
        ("GOODS_DEL_TIME", soup.find("input", {"id": "GOODS_DEL_TIME"}).get("value", "00:00:00")),
        ("UNIT_RECV_DATE", extract_js_variable(soup, "_l.UNIT_RECEIVED_DATE")),
        ("UNIT_RECV_TIME", soup.find("input", {"id": "UNIT_RECV_TIME"}).get("value", "00/00/0000")),
        ("FIRST_APP_DATE", extract_js_variable(soup, "_l.FIRST_APP_DATE")),
        ("FIRST_APP_TIME", soup.find("input", {"id": "FIRST_APP_TIME"}).get("value", "00:00:00")),
        ("FIRST_VISIT_DATE", extract_js_variable(soup, "_l.FIRST_VISIT_DATE") or ""),
        ("FIRST_VISIT_TIME", soup.find("input", {"id": "FIRST_VISIT_TIME"}).get("value", "")),
        ("ENG_ASSIGN_DATE", extract_js_variable(soup, "_l.ENG_ASSIGN_DATE")),
        ("ENG_ASSIGN_TIME", extract_js_variable(soup, "_l.ENG_ASSIGN_TIME")),
        ("LAST_APP_DATE", extract_js_variable(soup, "_l.LAST_APP_DATE")),
        ("LAST_APP_TIME", soup.find("input", {"id": "LAST_APP_TIME"}).get("value", "00:00:00")),
        ("LAST_VISIT_DATE", extract_js_variable(soup, "_l.LAST_VISIT_DATE") or "00/00/0000"),
        ("LAST_VISIT_TIME", soup.find("input", {"id": "LAST_VISIT_TIME"}).get("value", "00:00:00")),
        ("REPAIR_COMP_DATE", extract_js_variable(soup, "_l.REPAIR_COMP_DATE") or "00/00/0000"),
        ("REPAIR_COMP_TIME", extract_js_variable(soup, "_l.REPAIR_COMP_TIME") or "00:00:00"),
        ("CC_APP_DATE", soup.find("input", {"id": "CC_APP_DATE"}).get("value", "00/00/0000")),
        ("CC_APP_TIME", soup.find("input", {"id": "CC_APP_TIME"}).get("value", "00:00:00")),
        ("REQUEST_DATE", extract_js_variable(soup, "_l.CUST_REQ_DATE")),
        ("REQUEST_TIME", extract_js_variable(soup, "_l.CUST_REQ_TIME")),
        ("FROM_CUST_DATE", ""),
        ("TO_ASC_DATE", soup.find("input", {"id": "TO_ASC_DATE"}).get("value", "")),
        ("NEW_STD_PRICE_SHOW", ""),
        ("NEW_STD_PRICE", ""),
        ("NEW_STD_CHECK", ""),
        ("NEW_LCD_PRICE_SHOW", ""),
        ("NEW_LCD_PRICE", ""),
        ("NEW_LCD_CHECK", ""),
        ("NEW_PBA_PRICE_SHOW", ""),
        ("NEW_PBA_PRICE", ""),
        ("NEW_PBA_CHECK", ""),
        ("DISCOUNT_PRICE_SHOW", ""),
        ("DISCOUNTED_PRICE", ""),
        ("DISCOUNT_CHECK", ""),
        ("FREE_CHECK", ""),
        ("F_FREE", ""),
        ("NEW_TOTAL_AMT", ""),
        ("IO_FLAG", "T"),
        ("IV_TR_NO", ""),
        ("IV_GD_RESULT", soup.find("input", {"id": "IV_GD_RESULT"}).get("value", "X")),
        ("IO_FLAG", "I"),
        ("IO_FLAG", "O"),
        ("IO_FLAG", "R"),
        ("WTY_BILL_NO_", ""),
        ("SOLASTCHANGEDDATE", soup.find("input", {"id": "SOLASTCHANGEDDATE"}).get("value", data_atual)),
        ("SOLASTCHANGEDTIME", soup.find("input", {"id": "SOLASTCHANGEDTIME"}).get("value", hora_gmt0)),
        ("ASC_ACCNO", ""),
        ("COMPANY", ""),
        ("zpo", soup.find("input", {"id": "zpo"}).get("value", "")),
        ("SERVICE_COMPANY", extract_js_variable(soup, "_l.ticketCompany") or "C820"),
        ("TICKET_COMPANY", extract_js_variable(soup, "_l.ticketCompany") or "C820"),
        ("EXT_USER", soup.find("input", {"id": "ext_user"}).get("value", "usernaoencontrado")),
        ("INV_FLAG", ""),
        ("WTY_FLAG", ""),
        ("cmd", "ZifGspnSvcModifyLmEHNCmd"),
        ("MAC", ""),
        ("MAC_FLAG", ""),
        ("WTY_EXCEPTION_DB", extract_js_variable(soup, "_l.WTY_EXCEPTION")),
        ("IN_OUT_WTY_DB", extract_js_variable(soup, "_l.IN_OUT_WTY")),
        ("i_indicator", "SVCORDER"),
        ("TR_TYPE", extract_js_variable(soup, "_l.TR_TYPE") or "I"),
        ("STREET3", soup.find("input", {"id": "STREET3"}).get("value", "")),
        ("STREET2", soup.find("input", {"id": "STREET2"}).get("value", "")),
        ("STREET1", soup.find("input", {"id": "STREET1"}).get("value", "")),
        ("DISTRICT", soup.find("input", {"id": "DISTRICT"}).get("value", "")),
        ("REGION_CODE", extract_js_variable(soup, "_l.bpRegionCode")),
        ("COUNTRY", extract_js_variable(soup, "_l.COUNTRY") or "BR"),
        ("OFFICE_PHONE", soup.find("input", {"id": "OFFICE_PHONE"}).get("value", "")),
        ("CITY_CODE", soup.find("input", {"id": "CITY_CODE"}).get("value", "")),
        ("POSTAL_CODE", extract_js_variable(soup, "_l.bpPostCode")),
        ("FREIGHT", soup.find("input", {"id": "FREIGHT"}).get("value", "0.00")),
        ("OTHER", soup.find("input", {"id": "OTHER"}).get("value", "0.00")),
        ("SAWOTHER", soup.find("input", {"id": "SAWOTHER"}).get("value", "0.0")),
        ("MOBILE_PHONE", extract_js_variable(soup, "_l.mobile_phone")),
        ("HOME_PHONE", extract_js_variable(soup, "_l.HOME_PHONE")),
        ("isOutBound", extract_js_variable(soup, "_l.isOutBound") or "false"),
        ("prodInfoCon", soup.find("input", {"id": "prodInfoCon"}).get("value", "")),
        ("MB_IF_YN", extract_js_variable(soup, "_l.MB_IF_YN") or ""),
        ("MB_IF_RT_YN", extract_js_variable(soup, "_l.MB_IF_RT_YN") or ""),
        ("MB_IF_RT_INFO", soup.find("input", {"id": "MB_IF_RT_INFO"}).get("value", "111")),
        ("MB_IF_VERSION", soup.find("input", {"id": "MB_IF_VERSION"}).get("value", "")),
        ("MIF_LOG_FILE_YN", soup.find("input", {"id": "MIF_LOG_FILE_YN"}).get("value", "")),
        ("MB_IF_TR", soup.find("input", {"id": "MB_IF_TR"}).get("value", "")),
        ("MB_IF_MODEL", soup.find("input", {"id": "MB_IF_MODEL"}).get("value", "")),
        ("MB_IF_SERIAL", soup.find("input", {"id": "MB_IF_SERIAL"}).get("value", "")),
        ("MB_IF_IMEI", soup.find("input", {"id": "MB_IF_IMEI"}).get("value", "")),
        ("MB_IF_IMEI2", ""),
        ("MB_IF_UN", soup.find("input", {"id": "MB_IF_UN"}).get("value", "")),
        ("MB_IF_ROOTING", soup.find("input", {"id": "MB_IF_ROOTING"}).get("value", "")),
        ("UN_IO", soup.find("input", {"id": "UN_IO"}).get("value", "")),
        ("MIF_REPAIR", soup.find("input", {"id": "MIF_REPAIR"}).get("value", "")),
        ("MIF_UN_IO", soup.find("input", {"id": "MIF_UN_IO"}).get("value", "")),
        ("DIA_SKU", soup.find("input", {"id": "DIA_SKU"}).get("value", "")),
        ("DIA_SW_VERSION", soup.find("input", {"id": "DIA_SW_VERSION"}).get("value", "")),
        ("DIA_VERSION", soup.find("input", {"id": "DIA_VERSION"}).get("value", "X")),
        ("DIA_DATE", soup.find("input", {"id": "DIA_DATE"}).get("value", "")),
        ("DIA_TIME", soup.find("input", {"id": "DIA_TIME"}).get("value", "")),
        ("DIA_VERSION_CHECK", soup.find("input", {"id": "DIA_VERSION_CHECK"}).get("value", "")),
        ("DIA_RESULT", soup.find("input", {"id": "DIA_RESULT"}).get("value", "")),
        ("DIA_ERROR", soup.find("input", {"id": "DIA_ERROR"}).get("value", "")),
        ("DIA_RESULT_CODE", soup.find("input", {"id": "DIA_RESULT_CODE"}).get("value", "")),
        ("DIA_CHECK_FLAG", soup.find("input", {"id": "DIA_CHECK_FLAG"}).get("value", "Y")),
        ("DIA_METHOD", soup.find("input", {"id": "DIA_METHOD"}).get("value", "O")),
        ("SES_FLAG", soup.find("input", {"id": "SES_FLAG"}).get("value", "A")),
        ("IV_TEST_END_TIME", soup.find("input", {"id": "IV_TEST_END_TIME"}).get("value", "")),
        ("GD_SESS_ID", soup.find("input", {"id": "GD_SESS_ID"}).get("value", "")),
        ("GD_RESULT_TYPE", soup.find("input", {"id": "GD_RESULT_TYPE"}).get("value", "OQC")),
        ("LATEST_VER", soup.find("input", {"id": "LATEST_VER"}).get("value", ";;")),
        ("SW_VER", soup.find("input", {"id": "SW_VER"}).get("value", "")),
        ("PROCESS_ID", soup.find("input", {"id": "PROCESS_ID"}).get("value", "")),
        ("GD_BASE_URL", soup.find("input", {"id": "GD_BASE_URL"}).get("value", "")),
        ("GD_SKIPSAVE", soup.find("input", {"id": "GD_SKIPSAVE"}).get("value", "")),
        ("DIA_TYPE", soup.find("input", {"id": "DIA_TYPE"}).get("value", "")),
        ("REDO", soup.find("input", {"id": "REDO"}).get("value", "")),
        ("IV_GUBUN", soup.find("input", {"id": "IV_GUBUN"}).get("value", "S")),
        ("IV_AUTO_FLAG", soup.find("input", {"id": "IV_AUTO_FLAG"}).get("value", "S")),
        ("MIF_IO", soup.find("input", {"id": "MIF_IO"}).get("value", "")),
        ("MIF_COMPARE_FLAG", soup.find("input", {"id": "MIF_COMPARE_FLAG"}).get("value", "N")),
        ("CURR_MODEL", soup.find("input", {"id": "CURR_MODEL"}).get("value", "")),
        ("CURR_SERIAL_NO", soup.find("input", {"id": "CURR_SERIAL_NO"}).get("value", "")),
        ("CURR_IMEI", soup.find("input", {"id": "CURR_IMEI"}).get("value", "")),
        ("CURR_MIF_IO", soup.find("input", {"id": "CURR_MIF_IO"}).get("value", "")),
        ("BP_TYPE", soup.find("input", {"id": "BP_TYPE"}).get("value", "C001")),
        ("MAIN_FLAG", soup.find("input", {"id": "MAIN_FLAG"}).get("value", "")),
        ("GENERAL_FLAG", soup.find("input", {"id": "GENERAL_FLAG"}).get("value", "X")),
        ("CUSTOMER_FLAG", soup.find("input", {"id": "CUSTOMER_FLAG"}).get("value", "")),
        ("PRODUCT_FLAG", soup.find("input", {"id": "PRODUCT_FLAG"}).get("value", "")),
        ("JOB_FLAG", soup.find("input", {"id": "JOB_FLAG"}).get("value", "")),
        ("REPAIR_FLAG", soup.find("input", {"id": "REPAIR_FLAG"}).get("value", "")),
        ("SHIPPING_FLAG", soup.find("input", {"id": "SHIPPING_FLAG"}).get("value", "")),
        ("PENDPRO_FLAG", soup.find("input", {"id": "PENDPRO_FLAG"}).get("value", "")),
        ("SUBENG_FLAG", soup.find("input", {"id": "SUBENG_FLAG"}).get("value", "")),
        ("PSAPP", soup.find("input", {"id": "PSAPP"}).get("value", "")),
        ("TODATE", soup.find("input", {"id": "TODATE"}).get("value", "")),
        ("TOTIME", soup.find("input", {"id": "TOTIME"}).get("value", "")),
        ("ACT_DATE", soup.find("input", {"id": "ACT_DATE"}).get("value", "")),
        ("ACT_MOBILE_NO", soup.find("input", {"id": "ACT_MOBILE_NO"}).get("value", "")),
        ("SVC_PROVIDER", soup.find("input", {"id": "SVC_PROVIDER"}).get("value", "")),
        ("BOS_FLAG", soup.find("input", {"id": "BOS_FLAG"}).get("value", "")),
        ("PURCHASE_DT", soup.find("input", {"id": "PURCHASE_DT"}).get("value", "")),
        ("BOS_REASON", soup.find("input", {"id": "BOS_REASON"}).get("value", "")),
        ("ISCPSOCN", soup.find("input", {"id": "ISCPSOCN"}).get("value", "")),
    ])
    #for key, value in payload_fields:
        #print(f"{key}: {value}")
    dados_full ['payload_os_full'] = payload_fields
    return dados_full

def extract_js_variable(soup, var_name):
    script_tags = soup.find_all('script', type='text/javascript')
    for script in script_tags:
        if script.string:
            # Special handling for boolean values
            if var_name == "_l.isOutBound" or var_name.endswith(".isOutBound"):
                match = re.search(rf'{var_name}\s*=\s*(true|false)\s*;', script.string)
                if match:
                    return match.group(1)
            # Regular pattern for other variables
            match = re.search(rf'{var_name}\s*=\s*["\'](.*?)["\'](;?)', script.string) or re.search(rf'{var_name}\s*=\s*([^;\n]*)(;|\n|$)', script.string)
            if match:
                return match.group(1).strip()
    return ""

# Função para extrair valores de arrays ou objetos JS
def extract_js_object_value(soup, obj_name, key):
    script_tags = soup.find_all('script', type='text/javascript')
    for script in script_tags:
        if script.string and obj_name in script.string:
            match = re.search(rf'{obj_name}\.{key}\s*=\s*["\'](.*?)["\'](;?)', script.string) or re.search(rf'{obj_name}\.{key}\s*=\s*([^;\n]+)', script.string)
            if match:
                return match.group(1).strip() if match.group(1) else ""
    return ""

def obter_dados_saw(object_id, cookies=None):
    """
    Obtém as informações SAW via requisição HTTP
    
    Args:
        object_id: ID do objeto
        cookies: Cookies para autenticação. Se None, usa cookies de teste.
        
    Returns:
        Lista de tuplas com os campos SAW_STATUS e SAW_CATEGORY para cada item da tabela
        Retorna lista vazia se não encontrar valores válidos
    """
    # Parâmetros da requisição
    params = {
        "cmd": "ZifGspnSvcSawLDCmd",
        "objectId": object_id,
        "ascCode": "0002446971",  # Este é um valor padrão, poderia ser obtido dinamicamente
        "tab": "/svctracking/lite/ServiceOrderUpdateSaw.jsp"
    }
    
    # Cabeçalhos HTTP padronizados para todas as requisições
    headers = {
        "Host": "biz6.samsungcsportal.com",
        "Connection": "keep-alive",
        "X-Prototype-Version": "1.7.2",
        "sec-ch-ua-platform": "Windows",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Microsoft Edge\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://biz6.samsungcsportal.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://biz6.samsungcsportal.com/gspn/operate.do?UI=&currTabId=divJob",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    }
    
    # Cookies de teste, caso nenhum cookie seja fornecido
    test_cookies = {
        "WMONID": "R-zMlV5aRF9",
        "AMOBGSPNSESSIONID": "jUWQQcP18dQ0M5adsPEKdW7JpF2bela0kKXHjq9hZ04NV3M11FSO!112342113!-194814616",
        "visid_incap_2651221": "FaW+Zjh6Q2GIZY1CEF9wti0D02cAAAAAQUIPAAAAAAC+wdhJfmcER0IfDlI1woYI",
        "incap_ses_1588_2651221": "+98MXhUQVivb/LNW17UJFi0D02cAAAAAr9GcXMf+UsPGNksI5l72TA==",
        "dtPC": "-"
    }
    
    # Usa os cookies fornecidos ou os cookies de teste
    req_cookies = cookies if cookies else test_cookies
    
    try:
        # Fazemos a requisição HTTP com os cabeçalhos e cookies especificados
        response = requests.post(
            "https://biz6.samsungcsportal.com/gspn/operate.do",
            data=params,
            headers=headers,
            cookies=req_cookies,
            verify=False
        )
        
        # Verificamos se a resposta é válida
        if response.status_code == 200:
            # Extraímos os campos da tabela
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procuramos por todos os inputs hidden com os campos que precisamos
            saw_fields = []
            
            # Verificamos se existe uma tabela SAW válida
            saw_table = soup.find('table', {'class': 'tb_brdr2'})
            if not saw_table:
                print("Tabela SAW não encontrada na resposta")
                return []
                
            # Buscamos os inputs hidden dentro da tabela
            hidden_inputs = soup.find_all('input', {'type': 'hidden', 'name': ['SAW_STATUS', 'SAW_CATEGORY']})
            
            # Se não encontramos inputs hidden na tabela, retornamos lista vazia
            if not hidden_inputs:
                #print("Inputs hidden SAW_STATUS e SAW_CATEGORY não encontrados")
                return []
            
            # Agrupamos os campos por pares (SAW_STATUS e SAW_CATEGORY)
            statuses = [i for i in hidden_inputs if i.get('name') == 'SAW_STATUS']
            categories = [i for i in hidden_inputs if i.get('name') == 'SAW_CATEGORY']
            
            # Para cada par, adicionamos uma entrada na lista APENAS se ambos tiverem valores
            for i in range(min(len(statuses), len(categories))):
                status_value = statuses[i].get('value', '')
                category_value = categories[i].get('value', '')
                
                # Só adicionamos se ambos os valores não estiverem vazios
                if status_value and category_value:
                    saw_fields.append(
                        [("SAW_STATUS", status_value), 
                         ("SAW_CATEGORY", category_value)]
                    )
            
            return saw_fields
            
    except Exception as e:
        print(f"Erro ao obter dados SAW: {e}")
    
    # Em caso de erro, retornamos lista vazia
    return []


def pl_deletar_pecas(dados_full):
    html_content = dados_full['html_os']
    soup = BeautifulSoup(html_content, 'html.parser')
    
    payload = {
        "openTabID": "",
        "jobServiceType": soup.find("input", {"name": "jobServiceType"}).get("value", "CI") if soup.find("input", {"name": "jobServiceType"}) else "CI",
        "SOLASTCHANGEDDATE": soup.find("input", {"id": "SOLASTCHANGEDDATE"}).get("value", data_atual),
        "SOLASTCHANGEDTIME": soup.find("input", {"id": "SOLASTCHANGEDTIME"}).get("value", hora_gmt0),
        "STATE2": soup.find("input", {"id": "STATE2"}).get("value", ""),
        "LAST_APP_DATE": extract_js_variable(soup,"_l.LAST_APP_DATE"),
        "frYear": "",
        "toYear": "",
        "frMonth": "",
        "toMonth": "",
        "IV_PARTS_CODE": "",
        "IV_DATE": soup.find("input", {"id": "IV_DATE"}).get("value", ""),
        "fromListButton": "",
        "SAWPART": "",
        "PART_SERIAL": "",
        "PART_TERM": "O",
        "soDetailType": "",
        "jspName": "",
        "dataChange": "X",
        "p_listCall": "X",
        "cmd": "ServiceOrderPartsDeleteCmd",
        "objectID": soup.find("input", {"id": "objectID"}).get("value"),
        "gi_ASC_JOB_NO": soup.find('input', {'id': 'ASC_JOB_NO'}).get('value', ''),
        "assignedFlag": "X",
        "ascCode": "0002446971",
        "customerCode": soup.find("input", {"id": "customerCode"}).get("value"),
        "msg_seqno": "",
        "msgGuid": "",
        "msgText": "",
        "isawNo": "",
        "partsUsed": "",
        "wtyInOut": soup.find("input", {"id": "wtyInOut"}).get("value"),
        "IV_OBJKEY": "",
        "file_name": "",
        "fileSize": "",
        "Ctype": "NSAM-C,NSAM-D,NSAM-R,NSAM-S",
        "Code": "",
        "MODEL": soup.find("input", {"id": "MODEL"}).get("value"),
        "SERIAL": soup.find("input", {"id": "SERIAL"}).get("value"),
        "IMEI": soup.find("input", {"id": "IMEI"}).get("value"),
        "PRODUCT_DATE": soup.find("input", {"id": "PRODUCT_DATE"}).get("value"),
        "SYMPTOM_CAT1": soup.find("input", {"id": "SYMPTOM_CAT1"}).get("value"),
        "SYMPTOM_CAT2": soup.find("input", {"id": "SYMPTOM_CAT2"}).get("value"),
        "SYMPTOM_CAT3": "",
        "claimno": "",
        "wty_err_flag": "",
        "MBLNR": "",
        "MJAHR": "",
        "gi_material": "",
        "gi_qty": "",
        "gi_seq_no": "",
        "gi_engineer": "",
        "gi_engineer_nm": "",
        "gi_postingFlag": "",
        "gi_partWty": "",
        "cancelFlag": "",
        "svcPrcd": "THB02",
        "quotationFlag": "",
        "billingSearch": "",
        "hasWtyBilling": "",
        "model_p": "",
        "serialNo_p": "",
        "ASC_CODE_p": "",
        "IV_OBJECT_ID": soup.find("input", {"id": "objectID"}).get("value"),
        "interMessageType": "",
        "IRIS_CONDI": "",
        "IRIS_SYMPT": "",
        "IRIS_DEFECT": "",
        "IRIS_REPAIR": "",
        "IRIS_CONDI_DESC": "",
        "IRIS_SYMPT_DESC": "",
        "IRIS_DEFECT_DESC": "",
        "IRIS_REPAIR_DESC": "",
        "RetailInstallation": "",
        "additionalGasChargeForDVM": "",
        "canRedoMinorOption": "",
        "sameSAWCatCode": "",
        "canExtraPersonOption": "",
        "canExtraMileageHAOption": "",
        "sawExistCompressorSerialApproved": "",
        "sawExistSerialNoValidationApproved": "",
        "sawExistReverseVoidApproved": extract_js_variable(soup, "_l.sawExistReverseVoidApproved") or 'false',
        "highRisk": "",
        "defectType": "",
        "svcProd": "",
        "sawExistLabor": extract_js_variable(soup, "_l.sawExistLabor") or 'false',
        "bosFlag": "",
        "AUTH_GR": extract_js_variable(soup, "_l.AUTH_GR") or 'HHP',
        "PURCHASE_PLACE": "",
        "SAW_CATEGORY": "",
        "REASON": "",
        "currStatus": soup.find("input", {"id": "currStatus"}).get("value"),
        "autoDo": "",
        "cicProd": soup.find("input", {"id": "cicProd"}).get("value"),
        "hqSvcProd": soup.find("input", {"id": "hqSvcProd"}).get("value"),
        "ewpYn": "",
        "butlerX": "",
        "butlerXMsg": "",
        "sawExtraMileageApproved": "false",
        "relatedTicketAscCode": "",
        "mesChkFlag": "",
        "month": "",
        "IV_SAW_INCL_FLAG": soup.find("input", {"id": "IV_SAW_INCL_FLAG"}).get("value") or "X",
        "curSvcType": soup.find("input", {"id": "curSvcType"}).get("value") or "CI",
        "irnExist": "",
        "zzuniqueId": "",
        "IV_INOUTWTY": soup.find("input", {"id": "IV_INOUTWTY"}).get("value")
    }
    return payload
    
    