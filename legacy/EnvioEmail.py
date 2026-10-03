
import os
import sqlite3
from datetime import date, datetime
import smtplib
import email.message

def enviar_email():  
     
    with sqlite3.connect("barbearia.db") as con:
        cursor = con.cursor()
        query = '''SELECT nome_cliente, data_nascimento, email FROM clientes'''
        cursor.execute(query)
        
        # busca a data de hoje
        data_hoje = date.today().strftime("%d/%m")
        for row in cursor.fetchall():
            nome_cliente = row[0]
            data_nascimento = datetime.strptime(row[1], "%d/%m/%Y").strftime("%d/%m")
            email_cliente = row[2]
            
            if data_nascimento == data_hoje:
                    corpo_email =  f'''
                    <!DOCTYPE html>
                    <html lang="pt-br">
                    <head>
                        <meta charset="UTF-8">
                        <title>Feliz Aniversário!</title>
                    </head>
                    <body style="font-family: Arial, sans-serif; margin: 0; padding: 0; text-align: center; background-color: #f9f9f9;">
                        <div style="max-width: 600px; margin: 50px auto; background-color: #fff; border-radius: 10px; box-shadow: 0 0 10px rgba(0, 0, 0, 0.1); overflow: hidden;">
                            <div style="background-color: #4CAF50; color: #fff; padding: 20px;">
                                <h1 style="margin: 0; font-size: 2.5em;">🎉 Feliz Aniversário! 🎂</h1>
                            </div>
                            <img src="https://via.placeholder.com/600x250/4CAF50/ffffff?text=Parabéns%2C+{nome_cliente}!" alt="Parabéns!" style="width: 100%; height: auto; border-bottom: 1px solid #ddd;">
                            <div style="padding: 20px; font-size: 1.2em; line-height: 1.6; color: #333;">
                                <p>Olá <strong>Cliente Especial</strong>,</p>
                                <p>Hoje é um dia muito especial, e nós da <strong>Barbearia AD JOM</strong> não poderíamos deixar de celebrar com você!</p>
                                <p>Desejamos a você um dia cheio de alegria, saúde e sucesso. Que este novo ciclo traga muitas conquistas e momentos incríveis.</p>
                                <a href="#" style="display: inline-block; margin-top: 10px; padding: 10px 20px; background-color: #4CAF50; color: #fff; text-decoration: none; border-radius: 5px; font-weight: bold;">Ganhe um Presente Especial 🎁</a>
                            </div>
                            <div style="background-color: #f1f1f1; color: #777; padding: 10px; font-size: 0.9em;">
                                <p>Com carinho, <br><strong>Barbearia AD JOM</strong></p>
                            </div>
                        </div>
                    </body>
                    </html>


                        
                        '''

                    msg = email.message.Message()
                    msg['Subject'] = f"🎉 Feliz Aniversário, {nome_cliente}! Que esse dia seja muito especial para você!"
                    msg['From'] = os.environ['EMAIL_REMETENTE']
                    msg['To'] = f'{email_cliente}'
                    password = os.environ['EMAIL_SENHA_APP']
                    msg.add_header('Content-Type', 'text/html')
                    msg.set_payload(corpo_email)

                    s = smtplib.SMTP('smtp.gmail.com: 587')
                    s.starttls()
                    # Login Credentials for sending the mail
                    s.login(msg['From'], password)
                    s.sendmail(msg['From'], [msg['To']], msg.as_string().encode('utf-8'))
                    print('Email enviado')

    
            else:
                return
    

  

enviar_email()