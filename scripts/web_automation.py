from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
import os
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from a .env file located in the same directory as this script
load_dotenv()
uh_input_ = os.getenv('SEF_UH')
estabelecimento_input_ = os.getenv('SEF_ESTABELECIMENTO')
chave_activacao_input_ = os.getenv('SEF_CHAVE')
pdf_nif = os.getenv('PDF_NIF')
pdf_senha = os.getenv('PDF_SENHA')

# Extract the mapping files
countries_mapping = os.path.join(os.getcwd(), 'parameters', 'countries_mapping.json')
nationalities_mapping = os.path.join(os.getcwd(), 'parameters', 'nationalities_mapping.json')

# def fill_in_sef_form(df):

#     try:

#         with open(countries_mapping) as f:
#             countries = json.load(f)

#         with open(nationalities_mapping) as f:
#             nationalities = json.load(f)

#         web = webdriver.Chrome()

#         url = r'https://siba.sef.pt/s/FB.aspx?ReturnUrl=%2fs%2fbal%2fLotesEnvio.aspx'
#         web.get(url)

#         time.sleep(2)

#         # Find and fill in the input fields
#         uh_input = web.find_element('id', 'Conteudo_txtUH')
#         estabelecimento_input = web.find_element('id', 'Conteudo_txtEstabelecimento')
#         chave_activacao_input = web.find_element('id', 'Conteudo_txtChaveActivacao')

#         uh_input.send_keys(uh_input_)
#         estabelecimento_input.send_keys(estabelecimento_input_)
#         chave_activacao_input.send_keys(chave_activacao_input_)

#         # Locate and click the submit button
#         submit_button = web.find_element('id', 'Conteudo_btnConfirmar')
#         submit_button.click()

#         time.sleep(2)

#         # Create new list - NOTE: no need to comment this out as website won't allow you to create new list if one already exists
#         # Code will then run normally after time.sleep(2)
#         new_list = web.find_element('id', 'Conteudo_btnNovaLista')
#         new_list.click()

#         time.sleep(2)

#         # Edit new list
#         edit_list = web.find_element('id', 'Conteudo_dg_btnSelect_0')
#         edit_list.click()

#         time.sleep(2)

#         # Edit form
#         try:
#             edit_form = web.find_element('id', 'Conteudo_btnNovaBAL')
#             edit_form.click()
#         except:
#             # Click on save first
#             save = web.find_element('id', 'Conteudo_btnActualizarBAL')
#             save.click()
#             time.sleep(1)
#             edit_form = web.find_element('id', 'Conteudo_btnNovaBAL')
#             edit_form.click()

#         time.sleep(2)

#         ### START OF THE LOOP
#         for idx, row in df.iterrows():

#             # Get all fields
#             name_ = web.find_element('id', 'Conteudo_txtNome')
#             dob_ = web.find_element('id', 'Conteudo_txtDataNascimento')
#             nationality_ = web.find_element('id', 'Conteudo_lstNacionalidade')
#             country_of_res_ = web.find_element('id', 'Conteudo_lstPaisResidencia')
#             passport_ = web.find_element('id', 'Conteudo_txtNumPassaporteBI')
#             country_of_issue_ = web.find_element('id', 'Conteudo_lstPaisEmissor')
#             checkin_date_ = web.find_element('id', 'Conteudo_txtDataEntrada')
#             checkout_date_ = web.find_element('id', 'Conteudo_txtDataSaida')

#             # Write in fields
#             name = row['First name'] + ' ' + row['Last name']
#             name_.send_keys(name)

#             dob = row['Date of birth']
#             dob_.send_keys(dob)

#             nationality = countries[nationalities[row['Nationality']]]
#             nationality_.send_keys(nationality)

#             country_of_res = countries[row['Country of residence']]
#             country_of_res_.send_keys(country_of_res)

#             passport = row['Passport (or ID) number']
#             passport_.send_keys(passport)

#             country_of_issue = countries[row['Country of issue']]
#             country_of_issue_.send_keys(country_of_issue)

#             checkin_date = row['Check-in date']
#             checkin_date_.send_keys(checkin_date)

#             checkout_date = row['Check-out date']
#             checkout_date_.send_keys(checkout_date)

#             # Click on save
#             save = web.find_element('id', 'Conteudo_btnActualizarBAL')
#             save.click()

#             print('Details saved, going to next one')

#             time.sleep(3)

#         ### END OF THE LOOP

#         # Send the boletim
#         send = web.find_element('id', 'Conteudo_btnEnviarLista')
#         send.click()

#         time.sleep(10)

#         message = 'SEF Completed'

#         print(message)

#     except Exception as e:

#         print(f"Error: {e}")
#         message = e
    
#     return message

def fill_in_sef_form(df, callback):
    try:
        with open(countries_mapping) as f:
            countries = json.load(f)

        with open(nationalities_mapping) as f:
            nationalities = json.load(f)

        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        web = webdriver.Chrome(options=chrome_options)

        callback("Opening the SEF website...")
        url = 'https://siba.sef.pt/s/FB.aspx?ReturnUrl=%2fs%2fbal%2fLotesEnvio.aspx'
        web.get(url)
        time.sleep(2)

        callback("Filling in the establishment details...")
        uh_input = web.find_element('id', 'Conteudo_txtUH')
        estabelecimento_input = web.find_element('id', 'Conteudo_txtEstabelecimento')
        chave_activacao_input = web.find_element('id', 'Conteudo_txtChaveActivacao')

        uh_input.send_keys(uh_input_)
        estabelecimento_input.send_keys(estabelecimento_input_)
        chave_activacao_input.send_keys(chave_activacao_input_)

        submit_button = web.find_element('id', 'Conteudo_btnConfirmar')
        submit_button.click()
        time.sleep(2)

        callback("Creating a new list...")
        new_list = web.find_element('id', 'Conteudo_btnNovaLista')
        new_list.click()
        time.sleep(2)

        callback("Editing the new list...")
        edit_list = web.find_element('id', 'Conteudo_dg_btnSelect_0')
        edit_list.click()
        time.sleep(2)

        callback("Preparing to fill in guest details...")
        for idx, row in df.iterrows():
            name_ = web.find_element('id', 'Conteudo_txtNome')
            dob_ = web.find_element('id', 'Conteudo_txtDataNascimento')
            nationality_ = web.find_element('id', 'Conteudo_lstNacionalidade')
            country_of_res_ = web.find_element('id', 'Conteudo_lstPaisResidencia')
            passport_ = web.find_element('id', 'Conteudo_txtNumPassaporteBI')
            country_of_issue_ = web.find_element('id', 'Conteudo_lstPaisEmissor')
            checkin_date_ = web.find_element('id', 'Conteudo_txtDataEntrada')
            checkout_date_ = web.find_element('id', 'Conteudo_txtDataSaida')

            name = row['First name'] + ' ' + row['Last name']
            dob = row['Date of birth']
            nationality = countries[nationalities[row['Nationality']]]
            country_of_res = countries[row['Country of residence']]
            passport = row['Passport (or ID) number']
            country_of_issue = countries[row['Country of issue']]
            checkin_date = row['Check-in date']
            checkout_date = row['Check-out date']

            name_.send_keys(name)
            dob_.send_keys(dob)
            nationality_.send_keys(nationality)
            country_of_res_.send_keys(country_of_res)
            passport_.send_keys(passport)
            country_of_issue_.send_keys(country_of_issue)
            checkin_date_.send_keys(checkin_date)
            checkout_date_.send_keys(checkout_date)

            save = web.find_element('id', 'Conteudo_btnActualizarBAL')
            save.click()
            callback(f"Details for {name} saved. Proceeding to the next guest...")
            time.sleep(3)

        callback("Finalizing and sending the list...")
        # send = web.find_element('id', 'Conteudo_btnEnviarLista')
        # send.click()
        time.sleep(5)

        callback("SEF registration completed successfully.")

    except Exception as e:
        callback(f"Error during SEF registration: {e}")

    finally:
        web.quit()


def fill_in_invoice(filtered_df, amount, date=None, invoice_nif=None):

    if filtered_df.empty:
        print('Data provided is empty.')
        message = 'Data provided is empty.'
        return message
    
    # Extract info from df
    row = filtered_df.iloc[0]
    if not date:
        date = pd.to_datetime(row['Check-out date'], dayfirst=True).strftime('%Y-%m-%d')
    else:
        date = date.strftime('%Y-%m-%d')

    try:

        with open(countries_mapping) as f:
            countries = json.load(f)

        web = webdriver.Chrome()

        url = r'https://irs.portaldasfinancas.gov.pt/recibos/portal/emitir/emitirDocumentos'
        web.get(url)

        time.sleep(2)

        # Find the label element by its text content (assuming "NIF" is the text)
        label_element = web.find_element(By.XPATH, "//label[span='NIF']")

        # Click the label element to perform the action
        label_element.click()

        time.sleep(1)

        # Find and fill in the input fields
        nif = web.find_element('id', 'username')
        senha = web.find_element('id', 'password-nif')

        nif.send_keys(pdf_nif)
        senha.send_keys(pdf_senha)

        # Locate and click the submit button
        submit_button = web.find_element('id', 'sbmtLogin')
        submit_button.click()

        time.sleep(2)

        # Input date and type of invoice
        date_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-documentos-app-v2/emitir-documentos-form-v2/div[1]/div[2]/div/div/div/div[3]/div/div[1]/lf-date/div/div[1]/input')
        date_.send_keys(date)

        type_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-documentos-app-v2/emitir-documentos-form-v2/div[1]/div[2]/div/div/div/div[3]/div/div[2]/lf-dropdown/div/select')
        type_.send_keys('Fatura-Recibo')

        emitir_button = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-documentos-app-v2/emitir-documentos-form-v2/div[1]/div[2]/div/div/div/div[3]/div/div[3]/button')
        emitir_button.click()        

        time.sleep(2)

        # Get all fields
        country_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-adquirente/div/div[2]/div[1]/div[1]/lf-dropdown/div/select')
        name_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-adquirente/div/div[2]/div[2]/div/lf-text/div/input')
        payment_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[1]/pf-radio/div/div[1]/label/input')
        description_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[2]/div/textarea')
        iva_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[6]/div/div[1]/lf-dropdown/div/select')
        incidencia_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[7]/div[1]/div/lf-dropdown/div/select')
        amount_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[4]/div/div/div/input')
        selo_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-transmissao/div/div[2]/div[8]/div/div/div/input')
        first_emitir_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[1]/div[1]/div[1]/div[3]/button')
        second_emitir_ = web.find_element(By.XPATH, '//*[@id="emitirModal"]/div/div/div[3]/button[2]')

        # Write in fields
        country = countries[row['Country of residence']]
        country_.send_keys(country)

        if country.lower() == 'portugal':
            nif_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-adquirente/div/div[2]/div[1]/div[3]/lf-nif/div/input')
            nif_.send_keys(invoice_nif)
        else:
            passport_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app/emitir-form/div[1]/div[2]/div/dados-adquirente/div/div[2]/div[1]/div[2]/lf-text/div/input')
            passport = row['Passport (or ID) number']
            passport_.send_keys(passport)

        name = row['First name'] + ' ' + row['Last name']
        name_.send_keys(name)

        payment_.click()

        checkin_date = pd.to_datetime(row['Check-in date'], dayfirst=True).strftime('%d/%m/%Y')
        checkout_date = pd.to_datetime(row['Check-out date'], dayfirst=True).strftime('%d/%m/%Y')
        al_number = '138454/AL'
        address = 'RUA DE MARVILA N 54 R/C E 1950-199 LISBOA'
        description = f'Prestação de serviços de alojamento mobilado para turistas, da data {checkin_date} a {checkout_date}, no AL {al_number}, sito na morada: {address}'
        description_.send_keys(description)

        iva = 'IVA - regime de isenção [art.º 53.º]'
        iva_.send_keys(iva)

        incidencia = 'Sem retenção - Art.101º, n.º1 do CIRS'
        incidencia_.send_keys(incidencia)

        amount = amount
        amount_.send_keys(amount)

        selo = '0'
        selo_.send_keys(selo)

        time.sleep(2)

        first_emitir_.click()

        time.sleep(2)

        second_emitir_.click()
        
        time.sleep(5)

        message = 'Invoice Completed'

        print(message)

    except Exception as e:

        print(f"Error: {e}")
        message = e
    
    return message


