from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import io
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
        # url = 'https://siba.sef.pt/s/FB.aspx?ReturnUrl=%2fs%2fbal%2fLotesEnvio.aspx'
        url = 'https://siba.ssi.gov.pt/s/FB.aspx?ReturnUrl=%2fs%2fau%2fDefault.aspx'
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
        web.execute_script("arguments[0].click();", submit_button)
        time.sleep(2)

        entrega_dropdown = web.find_element(By.XPATH, '//*[@id="myNavbar"]/ul[1]/li[1]/a')
        boletins_button = web.find_element(By.XPATH, '//*[@id="myNavbar"]/ul[1]/li[1]/ul/li[1]/a')
        entrega_dropdown.click()
        boletins_button.click()
        time.sleep(2)

        callback("Creating a new list...")
        new_list = web.find_element('id', 'Conteudo_btnNovaLista')
        new_list.click()
        time.sleep(2)

        callback("Editing the list...")
        edit_list = web.find_element('id', 'Conteudo_dg_btnSelect_0')
        edit_list.click()
        time.sleep(2)

        try:
            callback("Trying to add new bulletin in case list already existed...")
            add_bulletin = web.find_element('id', 'Conteudo_btnNovaBAL')
            web.execute_script("arguments[0].click();", add_bulletin)
            callback("Added new bulleting...")
            time.sleep(2)
        except Exception as e:
            callback(f"Skipped adding new bulleting. Error: {e}")
            time.sleep(1)

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
        send = web.find_element('id', 'Conteudo_btnEnviarLista')
        send.click()
        time.sleep(3)

        callback("Done.")

    except Exception as e:
        callback(f"Error during SEF registration: {e}")

    finally:
        web.quit()


def fill_in_invoice(callback, filtered_df, amount, date=None, invoice_nif=None):

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

    # Initialize screenshot_stream at the beginning
    screenshot_stream = io.BytesIO()

    try:

        with open(countries_mapping, 'r', encoding='utf-8') as f:
            countries = json.load(f)

        # Run headlessly - comment out for debugging
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        web = webdriver.Chrome(options=chrome_options)
        # web = webdriver.Chrome() # NOTE: for debugging purposes

        callback("Opening the IRS website...")
        url = r'https://irs.portaldasfinancas.gov.pt/recibos/portal/emitir/emitirfaturaV2'
        web.get(url)

        time.sleep(2)

        callback("Filling in the login details...")
        # Find the NIF button
        label_element = web.find_element(By.XPATH, '//*[@id="radix-:r0:-trigger-N"]')
        

        # Click the label element to perform the action
        label_element.click()
        time.sleep(1)

        # Find and fill in the input fields
        nif = web.find_element(By.XPATH, '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[1]/div[2]/div/input')
        senha = web.find_element(By.XPATH, '/html/body/div/div/main/div[1]/div[3]/div[1]/div[3]/form/div[2]/div[2]/div/input')

        nif.send_keys(pdf_nif)
        senha.send_keys(pdf_senha)

        # Locate and click the submit button
        # submit_button = web.find_element('id', 'sbmtLogin')
        submit_button = web.find_element(By.XPATH, '//*[@id="radix-:r0:-content-N"]/form/button')
        submit_button.click()
        time.sleep(2)

        callback("Logged in successfully.")
        time.sleep(1)

        callback("Filling in the date and type of invoice...")
        # Input date and type of invoice
        date_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/div/dados-de-operacao-v2/div/div[3]/div[2]/div[1]/lf-date/div/div[1]/input')
        date_.send_keys(date)              

        type_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/div/dados-de-operacao-v2/div/div[3]/div[2]/div[2]/lf-dropdown/div/select')
        type_.send_keys('Fatura-Recibo')
          
        time.sleep(2)

        callback("Filling in the invoice details...")
        # Get all fields
        country_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[1]/lf-dropdown/div/select')      
        name_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[2]/div/lf-text/div/input')
        payment_ = web.find_element(By.XPATH, '//*[@id="motivoEmissao"]/div/div/pf-radio/div/div[1]/label/input')
        add_service_ = web.find_element(By.XPATH, '//*[@id="Bens&ServicosFT"]/div/div/table/tfoot/tr/td/button')

        # Write in fields
        country = countries[row['Country of residence']]
        country_.send_keys(country)

        if country.lower() == 'portugal':
            nif_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-nif/div/input')
            nif_.send_keys(invoice_nif)
        else:
            passport_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[2]/div/dados-adquirente-v2/div[1]/div[2]/div[1]/div[2]/lf-text/div/input')
            passport = row['Passport (or ID) number']
            passport_.send_keys(passport)

        name = row['First name'] + ' ' + row['Last name']
        name_.send_keys(name)

        payment_.click()
        add_service_.click()
        time.sleep(2)

        # Find additional fields
        type_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[1]/lf-dropdown/div/select')
        type_ref = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[4]/div[2]/lf-dropdown/div/select')
        reference_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[5]/div/lf-text/div/input')
        description_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[6]/div/lf-textarea/div/textarea')
        unit_ = web.find_element(By.XPATH,'//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[8]/div[2]/lf-dropdown/div/select')
        amount_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[8]/div[3]/div/input')
        iva_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[2]/div/div[10]/div[1]/lf-dropdown/div/select')
        guardar_ = web.find_element(By.XPATH, '//*[@id="adicionarProdutosModal"]/adicionar-produtos/div/div/div[3]/button[2]')

        type_.send_keys('Serviço')
        type_ref.send_keys('Outro')
        reference_.send_keys('Alojamento Local')

        checkin_date = pd.to_datetime(row['Check-in date'], dayfirst=True).strftime('%d/%m/%Y')
        checkout_date = pd.to_datetime(row['Check-out date'], dayfirst=True).strftime('%d/%m/%Y')
        al_number = '138454/AL'
        address = 'RUA DE MARVILA N 54 R/C E 1950-199 LISBOA'
        description = f'Prestação de serviços de alojamento mobilado para turistas, da data {checkin_date} a {checkout_date}, no AL {al_number}, sito na morada: {address}'
        description_.send_keys(description)

        unit_.send_keys('N/A')

        amount = float(amount)
        amount = round(amount/1.06, 2) # Remove the 6% VAT
        amount = str(amount)

        # Make sure there are two decimal places
        if '.' not in amount:
            amount = amount + '.00'
        elif len(amount.split('.')[1]) == 1:
            amount = amount + '0'
        
        amount_.send_keys(amount)

        iva = '6%'
        iva_.send_keys(iva)

        # Capture the screenshot directly into a BytesIO object
        screenshot_stream.write(web.get_screenshot_as_png())
        screenshot_stream.seek(0)  # Move to the beginning of the stream

        guardar_.click()
        time.sleep(1)

        callback("Submitting the invoice (first button)...")
        first_emitir_ = web.find_element(By.XPATH, '//*[@id="main-content"]/div/div/emitir-app-v2/emitir-form-v2/div[1]/div[1]/div[1]/div[1]/div[2]/button')
        web.execute_script("arguments[0].click();", first_emitir_)  
        time.sleep(2)

        callback("Submitting the invoice (second button)...")
        second_emitir_ = web.find_element(By.XPATH, '//*[@id="confirmarEmissaoModal"]/confirmar-emissao/div/div/div[3]/button[2]')
        web.execute_script("arguments[0].click();", second_emitir_)  
        time.sleep(2)

        # time.sleep(20) # NOTE: for debugging purposes when running automation in browser

        callback("Done.")

    except Exception as e:
        callback(f"Error when issuing the invoice: {e}")

        # Optionally capture a screenshot at the point of error if possible
        screenshot_stream.write(web.get_screenshot_as_png())
        screenshot_stream.seek(0)

    finally:
        web.quit()
        return screenshot_stream

