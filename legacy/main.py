import tkinter as tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkcalendar import Calendar, DateEntry
import sqlite3
from tkinter import messagebox
import phonenumbers
from phonenumbers import geocoder, carrier, is_valid_number
from email_validator import validate_email, EmailNotValidError
from agendamento import *
from tkinter import filedialog
from datetime import date, datetime



class barbearia:
    def __init__(self):
        self.windows = ttk.Window(themename="darkly")
        self.style = ttk.Style()
        self.style.configure('Treeview.Heading', font=('Arial', 12, "bold"))
        self.style.configure("TNotebook.Tab", font=("Arial", 12,"bold"))
        self.style.configure("Custom.TNotebook.Tab", padding=[10,5])
        self.style.configure("TLabel", font=("Arial", 13,"bold"))
        self.style.configure("TEntry", font=("Arial", 13))
        self.windows.title("Barbearia")
        self.windows.geometry("1500x700")
        self.windows.resizable(0,0)
        self.frame_title = ttk.Frame(self.windows)
        self.frame_title.pack(fill="x")
        self.image = ttk.PhotoImage(file="logo-440x240.png")
        self.label_image_logo = ttk.Label(self.frame_title, image=self.image) #label para a imagem
        self.label_image_logo.pack(side="left", padx=10)
        self.label_title = ttk.Label(self.frame_title, text="BARBEARIA ADJOM", font="Arial 25 bold",foreground="white")
        self.label_title.pack(pady=25, anchor=CENTER)
        self.windows_notebook = ttk.Notebook(self.windows, bootstyle="info", style="Custom.TNotebook")
        self.windows_notebook.pack(fill="x", expand=False)
        self.frame_atualizacoes = ttk.Labelframe(self.windows, text="Atualizações")
        self.frame_atualizacoes.pack(fill="both", expand=True)
        self.label_atualizacoes = ttk.Label(self.frame_atualizacoes, text="Hoje é o aniversário de: ")
        self.label_atualizacoes.grid(row=0, column=0)

        # FRAMES
        self.tela_de_clientes = ttk.Frame(self.windows_notebook)
        self.tela_de_clientes.pack(fill="both", expand=True)
        self.tela_de_atendimento = ttk.Frame(self.windows_notebook)
        self.tela_de_atendimento.pack(fill="both", expand=True)

        self.tela_de_agendamento = ttk.Frame(self.windows_notebook)
        self.tela_de_agendamento.pack(fill="both", expand=True)
       

        self.windows_notebook.add(self.tela_de_atendimento, text="Atendimento")
        self.windows_notebook.add(self.tela_de_clientes, text="Clientes")
        self.windows_notebook.add(self.tela_de_agendamento, text="Agendamento")

        # TELA DE ATENDIMENTO 

        self.frame_tela_de_atendimento = ttk.Frame(self.tela_de_atendimento)
        self.frame_tela_de_atendimento.pack(fill="x")

        # self.imagem1_tela_de_atendimento = ttk.Frame(self.tela_de_atendimento, relief="groove", border=10)
        # self.imagem1_tela_de_atendimento.pack(side="left")

        self.label_localizar_cliente_atendimento = ttk.Label(self.frame_tela_de_atendimento, text="Nome do Cliente:")
        self.label_localizar_cliente_atendimento.grid(row=0, column=0)
        self.combobox_clientes_atendimento = ttk.Combobox(self.frame_tela_de_atendimento, values=[""], width=50)
        self.combobox_clientes_atendimento.grid(row=0, column=1, pady=10)
        
        self.label_data_do_atendimento = ttk.Label(self.frame_tela_de_atendimento, text=" Data do Atendimento:")
        self.label_data_do_atendimento.grid(row=1, column=0)
        self.data_do_atendimento = ttk.DateEntry(self.frame_tela_de_atendimento, dateformat="%d/%m/%Y")
        self.data_do_atendimento.grid(row=1, column=1, pady=10)
        self.data_do_atendimento.entry.config(font="Arial 12", state=READONLY)

        self.servico_cliente = ttk.Label(self.frame_tela_de_atendimento, text="Serviço: ")
        self.servico_cliente.grid(row=2, column=0)
        self.combobox_servicos = ttk.Combobox(self.frame_tela_de_atendimento, values=[""], width=30)
        self.combobox_servicos.grid(row=2,column=1, pady=10)

        self.botao_adicionar_servico = ttk.Button(self.frame_tela_de_atendimento, text="Adicionar Serviço",command=self.adicionar_servico)
        self.botao_adicionar_servico.grid(row=2, column=2, pady=10)

        self.label_produto_atendimento = ttk.Label(self.frame_tela_de_atendimento, text="Produtos:")
        self.label_produto_atendimento.grid(row=4, column=0)
        self.combobox_produto_atendimento = ttk.Combobox(self.frame_tela_de_atendimento, values=[""], width=30)
        self.combobox_produto_atendimento.grid(row=4, column=1, pady=10)

        self.botao_adicionar_produto = ttk.Button(self.frame_tela_de_atendimento, text="Adicionar Produto",command=self.adicionar_produto)
        self.botao_adicionar_produto.grid(row=4, column=2)


       
        self.label_total_servico = ttk.Label(self.frame_tela_de_atendimento, text="Valor total: ")
        self.label_total_servico.grid(row=5,column=0)
        self.entry_valor_total = ttk.Entry(self.frame_tela_de_atendimento, state="disabled", width=30)
        self.entry_valor_total.grid(row=5,column=1, pady=10)

        self.frame_tree_servicos = ttk.Labelframe(self.tela_de_atendimento, text="Serviços")
        self.frame_tree_servicos.pack()

        columns = ('SERVIÇOS',"VALOR DO SERVIÇO")
        self.tree_servicos = ttk.Treeview(self.frame_tree_servicos, columns=columns, show="headings", height=5,  bootstyle=PRIMARY)
        self.tree_servicos.pack(fill="both", side="left", expand=True)

        self.tree_servicos.heading("SERVIÇOS",text="Serviços")
        self.tree_servicos.heading("VALOR DO SERVIÇO",text="Valor do serviço")
        self.tree_servicos.column("VALOR DO SERVIÇO", anchor=CENTER, width=500)
        self.tree_servicos.column("SERVIÇOS", anchor=CENTER, width=500)
        
        self.frame_botoes_atendimento = ttk.Frame(self.tela_de_atendimento)
        self.frame_botoes_atendimento.pack()
        self.botao_concluir = ttk.Button(self.frame_botoes_atendimento, text="Concluir atendimento",  command=self.concluir_atendimento)
        self.botao_concluir.grid(row=0, column=1, padx=10, pady=10)

        self.botao_deletar_item = ttk.Button(self.frame_botoes_atendimento, text="Deletar serviço", bootstyle= DANGER, command= lambda: self.deletar_servico('<<TreeviewSelect>>'))
        self.botao_deletar_item.grid(row=0, column=3, padx=10, pady=10)


        # TELA DE CLIENTES

        self.frame_tela_clientes = ttk.Frame(self.tela_de_clientes)
        self.frame_tela_clientes.pack()

       
        self.label_nome_cliente = ttk.Label(self.frame_tela_clientes, text="Nome do Cliente:")
        self.label_nome_cliente.grid(row=0, column=0, padx=10, pady=20)
        self.combobox_clientes = ttk.Combobox(self.frame_tela_clientes, values= [""], width=50)
        self.combobox_clientes.grid(row=0, column=1, padx=10, pady=1)
       
        
        self.label_telefone_cliente = ttk.Label(self.frame_tela_clientes, text="Telefone:")
        self.label_telefone_cliente.grid(row=0, column=2, pady=10, padx=10)
        self.entry_telefone_cliente = ttk.Entry(self.frame_tela_clientes, width=30, state=READONLY)
        self.entry_telefone_cliente.grid(row=0, column=3, padx=0, pady=5)

        self.label_email_cliente = ttk.Label(self.frame_tela_clientes, text="E-mail:")
        self.label_email_cliente.grid(row=2, column=0, pady=10, padx=10)
        self.entry_email_cliente = ttk.Entry(self.frame_tela_clientes, width=50, state=READONLY)
        self.entry_email_cliente.grid(row=2, column=1, padx=10, pady=10)
      

        self.label_data_nascimento_cliente = ttk.Label(self.frame_tela_clientes, text="Data de nascimento:")
        self.label_data_nascimento_cliente.grid(row=2, column=2, pady=10, padx=10)
        self.data_nascimento_cliente = ttk.DateEntry(self.frame_tela_clientes, dateformat="%d/%m/%Y")
        self.data_nascimento_cliente.grid(row=2, column=3, padx=10, pady=10)
        self.data_nascimento_cliente.entry.config(font="Arial 12", state=READONLY)
        
        self.label_endereco_cliente = ttk.Label(self.frame_tela_clientes, text="Endereço: ")
        self.label_endereco_cliente.grid(row=4, column=0,  padx=10, pady=10)
        self.entry_endereco_cliente = ttk.Entry(self.frame_tela_clientes, width=50, state=READONLY)
        self.entry_endereco_cliente.grid(row=4,column=1, padx=10, pady=10)
        
        self.frame_historico_pedidos = ttk.Labelframe(self.tela_de_clientes, text="Histórico do Cliente", width=200)
        self.frame_historico_pedidos.pack()

        # Configuração das colunas da Treeview

        columns = ("DATA", "SERVIÇO", "VALOR")

        # Inicialização da Treeview
        self.tree_historico_do_cliente = ttk.Treeview(self.frame_historico_pedidos,columns=columns,show="headings",height=5,  bootstyle=PRIMARY)
        self.tree_historico_do_cliente.pack(fill="both", side="left", expand=True)
        # Configuração das colunas
        self.tree_historico_do_cliente.heading("DATA", text="Data")
        self.tree_historico_do_cliente.heading("SERVIÇO", text="Serviço")
        self.tree_historico_do_cliente.heading("VALOR", text="Valor")

        self.tree_historico_do_cliente.column("DATA", anchor=CENTER, width=400)
        self.tree_historico_do_cliente.column("SERVIÇO", anchor=CENTER, width=400)
        self.tree_historico_do_cliente.column("VALOR", anchor=CENTER, width=400)

        # Barra de rolagem
        barra_clientes = ttk.Scrollbar(self.frame_historico_pedidos,orient="vertical",command=self.tree_historico_do_cliente.yview)
        barra_clientes.pack(fill="y", side="right", expand=False)
        self.tree_historico_do_cliente.configure(yscrollcommand=barra_clientes.set)

        # Botões no frame de cliente

        self.botoes_clientes = ttk.Frame(self.tela_de_clientes)
        self.botoes_clientes.pack()
        self.botao_cadastrar_novo_cliente = ttk.Button(self.botoes_clientes,text="Novo Cliente",command=self.novo_cliente)
        self.botao_cadastrar_novo_cliente.grid(row=0, column=0, padx=10, pady=20)
        self.botao_salvar_alteracao_cliente = ttk.Button(self.botoes_clientes,text="Salvar Alteração",command=self.salvar_alteracao_cliente)
        self.botao_salvar_alteracao_cliente.grid(row=0, column=1, padx=10, pady=20)
        self.botao_alterar_cliente = ttk.Button(self.botoes_clientes,text="Editar Cliente",command=self.editar_area_de_cliente)
        self.botao_alterar_cliente.grid(row=0, column=2, padx=10, pady=20)
        self.buscar_relatorio_cliente = ttk.Button(self.botoes_clientes, text="Extrair histórico", command=self.extrair_historico_cliente)
        self.buscar_relatorio_cliente.grid(row=0, column=3)
        self.botao_limpar_cliente = ttk.Button(self.botoes_clientes,text="Limpar",bootstyle="danger",width=17,command=self.limpar_tela_cliente)
        self.botao_limpar_cliente.grid(row=0, column=4, padx=10, pady=20)


        # TELA DE AGENDAMENTOS
        self.frame_agendamento = ttk.Frame(self.tela_de_agendamento)
        self.frame_agendamento.pack(fill="x", padx=50, pady=50)

        self.label_data_agendamento = ttk.Label(self.frame_agendamento, text=" Data de Agendamento: ")
        self.label_data_agendamento.grid(row=0, column=0)

        self.data_agendamento = ttk.DateEntry(self.frame_agendamento, dateformat="%d/%m/%Y")
        self.data_agendamento.grid(row=0, column=1)
        self.data_agendamento.entry.config(font="Arial 12")

        self.botao_pesquisar_agendamento = ttk.Button(self.frame_agendamento, text="Pesquisar", command=self.buscar_agendamentos)
        self.botao_pesquisar_agendamento.grid(row=0, column=2, padx=5)
        
        self.image_atualizar = ttk.PhotoImage(file=r"icons\icons-atualizar.png")
        self.botao_atualizar = ttk.Button(self.frame_agendamento, image=self.image_atualizar, command=self.atualizar_agendamentos_treeview)
        self.botao_atualizar.grid(row=0, column=3, padx=5)


        # Configuração das colunas da Treeview
        columns = ("DATA", "HORÁRIO", "CLIENTE", "SERVIÇO")

        # Inicialização da Treeview
        self.frame_tree_agendamento = ttk.Labelframe(self.tela_de_agendamento, text="Lista de agendamentos")
        self.frame_tree_agendamento.pack(fill="both", padx=20, pady=20)

        self.tree_agendamentos = ttk.Treeview(self.frame_tree_agendamento, columns=columns, show="headings", height=10, bootstyle=PRIMARY)
        self.tree_agendamentos.pack(fill="both", side="left", expand=True)
       

        # Configuração das colunas
        self.tree_agendamentos.heading("DATA", text="DATA")
        self.tree_agendamentos.heading("HORÁRIO", text="HORÁRIO")
        self.tree_agendamentos.heading("CLIENTE", text="CLIENTE")
        self.tree_agendamentos.heading("SERVIÇO", text="SERVIÇO")
        self.tree_agendamentos.column("DATA", anchor=CENTER)
        self.tree_agendamentos.column("HORÁRIO", anchor=CENTER)
        self.tree_agendamentos.column("CLIENTE", anchor=CENTER)
        self.tree_agendamentos.column("SERVIÇO", anchor=CENTER)

        # Barra de rolagem
        barra_agendamentos = ttk.Scrollbar(self.frame_tree_agendamento, orient="vertical", command=self.tree_agendamentos.yview)
        barra_agendamentos.pack(fill="y", side="right", expand=False)
        self.tree_agendamentos.configure(yscrollcommand=barra_agendamentos.set)

        self.frame_botoes_agendamento = ttk.Frame(self.tela_de_agendamento)
        self.frame_botoes_agendamento.pack()
        self.botao_novo_agendamento = ttk.Button(self.frame_botoes_agendamento, text="Novo atendimento", command=self.janela_novo_agendamento)
        self.botao_novo_agendamento.pack()


        self.combobox_clientes_atendimento.bind("<KeyRelease>",self.localizar_cliente_atendimento)
        self.combobox_clientes.bind("<KeyRelease>",self.localizar_cliente_atendimento)
        self.combobox_clientes.bind("<KeyRelease>",self.localizar_cliente)
        self.combobox_clientes.bind("<<ComboboxSelected>>",self.preencher_tela_clientes)
        self.lista_de_produtos()
        self.lista_de_servicos()
       
        self.windows.mainloop()
    
    

     
    def extrair_historico_cliente(self):
        cliente = self.combobox_clientes.get()

        if not cliente:
            messagebox.showwarning("Atenção", "Selecione um cliente.")
            return
        
        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            query = '''SELECT data_atendimento, descricao_item, valor FROM atendimentos WHERE nome_cliente = ?'''
            cursor.execute(query,(cliente,))
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            # criar o dataframe do cliente
            df = pd.DataFrame(rows, columns=columns)
            file_name = filedialog.asksaveasfilename(title="Salvar como", defaultextension=".xlsx",filetypes=[("Arquivo Excel","*.xlsx"),("Todos os arquivos","*.*")])
            
            df.to_excel(file_name, index=False)
        
            messagebox.showinfo("Concluído","Relatório extraído com sucesso.")
       
     

    def salvar_alteracao_cliente(self):

        nome = self.combobox_clientes.get()
        telefone = self.entry_telefone_cliente.get()
        email = self.entry_email_cliente.get()
        data = self.data_nascimento_cliente.entry.get()
        endereco = self.entry_endereco_cliente.get()

        if not all([nome,telefone,email,data,endereco]):
            messagebox.showerror("Entrada inválida.","Preencha todos os campos.") 
            return
        try:
            with sqlite3.connect("barbearia.db") as con:
                cursor = con.cursor()
                script = '''UPDATE clientes SET telefone = ?, email = ?, data_nascimento = ?, endereco = ? WHERE nome_cliente = ?'''
                values = (
                    telefone,
                    email,
                    data,
                    endereco,
                    nome
                )
                cursor.execute(script,values)
                con.commit()
                messagebox.showinfo("","Cliente atualizado.")
            
            self.entry_telefone_cliente.config(state=READONLY)
            self.entry_email_cliente.config(state=READONLY)
            self.data_nascimento_cliente.entry.config(state=READONLY)
            self.entry_endereco_cliente.config(state=READONLY)
        except:
            messagebox.showwarning("","Nenhum cliente atualizado.")

    def limpar_tela_cliente(self):
        self.combobox_clientes.delete(0, END)
        self.entry_telefone_cliente.config(state=NORMAL)
        self.entry_telefone_cliente.delete(0, END)
        self.entry_telefone_cliente.config(state=READONLY)
        self.entry_email_cliente.config(state=NORMAL)
        self.entry_email_cliente.delete(0, END)
        self.entry_email_cliente.config(state=READONLY)
        self.data_nascimento_cliente.entry.config(state=NORMAL)
        self.data_nascimento_cliente.entry.delete(0, END)
        self.data_nascimento_cliente.entry.config(state=READONLY)
        self.entry_endereco_cliente.config(state=NORMAL)
        self.entry_endereco_cliente.delete(0, END)
        self.entry_endereco_cliente.config(state=READONLY)
        for item in self.tree_historico_do_cliente.get_children():
            self.tree_historico_do_cliente.delete(item)
    


    def deletar_servico(self, event):
        selected_items = self.tree_servicos.selection()
        if not selected_items:
            return

        confirm = messagebox.askquestion("Atenção",message="Deseja realmente excluir esse serviço?") 

        if confirm == "yes":
            selected_item = self.tree_servicos.selection()[0]
            self.tree_servicos.delete(selected_item)
        else:
            return

    def editar_area_de_cliente(self):

        self.entry_telefone_cliente.config(state=NORMAL)
        self.entry_email_cliente.config(state=NORMAL)
        self.data_nascimento_cliente.entry.config(state=NORMAL)
        self.entry_endereco_cliente.config(state=NORMAL)




        
    def preencher_tela_clientes(self, event):
        cliente = self.combobox_clientes.get()

        with sqlite3.connect('barbearia.db') as con:
            cursor = con.cursor()
            query_idcliente = '''SELECT email, endereco, telefone, data_nascimento FROM clientes WHERE nome_cliente = ?'''
            cursor.execute(query_idcliente,(f'{cliente}',))

            for row in cursor.fetchall():
                self.entry_email_cliente.config(state=NORMAL)
                self.entry_email_cliente.delete(0, END)
                self.entry_email_cliente.insert(0, row[0])
                self.entry_email_cliente.config(state=READONLY)

                self.entry_endereco_cliente.config(state=NORMAL)
                self.entry_endereco_cliente.delete(0, END)
                self.entry_endereco_cliente.insert(0, row[1])
                self.entry_endereco_cliente.config(state=READONLY)

                self.entry_telefone_cliente.config(state=NORMAL)
                self.entry_telefone_cliente.delete(0, END)
                self.entry_telefone_cliente.insert(0, row[2])
                self.entry_telefone_cliente.config(state=READONLY)

                self.data_nascimento_cliente.entry.config(state=NORMAL)
                self.data_nascimento_cliente.entry.delete(0, END)
                self.data_nascimento_cliente.entry.insert(0, row[3])
                self.data_nascimento_cliente.entry.config(state=READONLY)

                query_idcliente = '''select data_atendimento, descricao_item, valor 
                from atendimentos where nome_cliente = ?
                '''
                
                cursor.execute(query_idcliente,(f'{cliente}',))
                for item in self.tree_historico_do_cliente.get_children():
                    print(item)
                    self.tree_historico_do_cliente.delete(item)
                for row in cursor.fetchall():
                    self.tree_historico_do_cliente.insert('', END, values=row)

    
    def novo_cliente(self):
        self.tela_novo_cliente = ttk.Toplevel()
        self.tela_novo_cliente.title("Novo Cliente")
        self.tela_novo_cliente.resizable(0,0)
        self.label_nome_cadastro = ttk.Label(self.tela_novo_cliente, text="Nome do cliente:")
        self.label_nome_cadastro.grid(row=0, column=0, pady=10, padx=10)   
        self.entry_nome_cadastro = ttk.Entry(self.tela_novo_cliente, width=50)
        self.entry_nome_cadastro.grid(row=0, column=1, pady=10, padx=10)

        self.label_telefone_cadastro = ttk.Label(self.tela_novo_cliente, text="Telefone:")
        self.label_telefone_cadastro.grid(row=1, column=0, pady=5)
        self.entry_telefoe_cadastro = ttk.Entry(self.tela_novo_cliente, width=50)
        self.entry_telefoe_cadastro.grid(row=1, column=1, pady=10, padx=10)
        self.label_validacao_telefone = ttk.Label(self.tela_novo_cliente, text="")
        self.label_validacao_telefone.grid(row=1, column=2)

        self.label_email_cadastro = ttk.Label(self.tela_novo_cliente, text="E-mail:")
        self.label_email_cadastro.grid(row=2, column=0, pady=5)
        self.entry_email_cadastro = ttk.Entry(self.tela_novo_cliente, width=50)
        self.entry_email_cadastro.grid(row=2, column=1, pady=10, padx=10)
        self.label_validacao_email = ttk.Label(self.tela_novo_cliente, text="")
        self.label_validacao_email.grid(row=2,column=2)

        self.label_data_nascimento_cadastro = ttk.Label(self.tela_novo_cliente, text="Data de nascimento:")
        self.label_data_nascimento_cadastro.grid(row=3, column=0, padx=5)
        self.data_nascimento_cadastro = ttk.DateEntry(self.tela_novo_cliente,  dateformat="%d/%m/%Y")
        self.data_nascimento_cadastro.grid(row=3, column=1, pady=10, padx=10)
        self.data_nascimento_cadastro.entry.config(font="Arial 12", foreground="white")
        
        self.frame_botao_cadastro = ttk.Frame(self.tela_novo_cliente)
        self.frame_botao_cadastro.grid(row=4, column=1)
        self.botao_cadastrar = ttk.Button(self.frame_botao_cadastro, text="Cadastrar", command=self.cadastrar_cliente)
        self.botao_cadastrar.grid(row=0, column=0, padx=20, pady=20)

        self.botao_limpar = ttk.Button(self.frame_botao_cadastro, text="Cancelar", bootstyle = DANGER, command=lambda: self.tela_novo_cliente.destroy())
        self.botao_limpar.grid(row=0, column=1, padx=20, pady=20)


    def lista_de_servicos(self):
        
        with sqlite3.connect("barbearia.db") as con:  
            cursor = con.cursor()
            cursor.execute('SELECT tipo_servico FROM servicos')

            self.servicos = [row[0] for row in cursor.fetchall()]
            self.combobox_servicos.config(values=self.servicos)

        return self.servicos
    
    def lista_de_servicos_agendamento(self):
        
        with sqlite3.connect("barbearia.db") as con:  
            cursor = con.cursor()
            cursor.execute('SELECT tipo_servico FROM servicos')

            self.servicos = [row[0] for row in cursor.fetchall()]
            self.combobox_servicos_novo_agendamento.config(values=self.servicos)

     
    
    def cadastrar_cliente(self, event=None):
        nome = self.entry_nome_cadastro.get().upper()
        telefone = self.entry_telefoe_cadastro.get()
        email = self.entry_email_cadastro.get()
        data = self.data_nascimento_cadastro.entry.get()

        
        if not all([nome,telefone,email,data]):
            messagebox.showerror("Entrada inválida.","Preencha todos os campos.") 
            return
        try:
           with sqlite3.connect("barbearia.db") as con:
                cursor = con.cursor()

                script = '''INSERT INTO clientes(nome_cliente,telefone,email,data_nascimento)
                VALUES(?,?,?,?)
                '''
                values = (
                    nome, 
                    telefone,
                    email,
                    data
                )

                cursor.execute(script,values)
                con.commit()
                messagebox.showinfo("","Cliente cadastrado com sucesso!")

                self.entry_nome_cadastro.delete(0, END), 
                self.entry_telefoe_cadastro.delete(0, END),
                self.entry_email_cadastro.delete(0, END),
                self.data_nascimento_cadastro.entry.delete(0, END)   
        except:
            messagebox.showwarning("","Nenhum cliente cadastrado.")   
    

    def adicionar_servico(self):

        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            servicos = self.combobox_servicos.get()
            script = '''
            SELECT tipo_servico, valor_servico FROM servicos WHERE tipo_servico = ?
            '''
            cursor.execute(script, (servicos,))
            # Obtendo o resultado da consulta
            resultado = cursor.fetchall()
            # Obtendo o valor atual do campo de valor total
            valor = self.entry_valor_total.get()
            if not valor:
                valor = 0
   
            for row in resultado:
                self.tree_servicos.insert('', END, values=row)
                self.entry_valor_total.delete(0, END)
                self.entry_valor_total.config(state=NORMAL)
                try :
                    valor = float(valor)
                except:
                    print("Coloque um valor válido.")
                total = valor + row[1]
                self.entry_valor_total.insert(0, total)

    def adicionar_produto(self):
        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            produto = self.combobox_produto_atendimento.get()
            query = ''' SELECT nome_produto, valor_produto FROM produtos WHERE nome_produto = ?'''
            cursor.execute(query,(produto,))
            resultado = cursor.fetchall()
            valor = self.entry_valor_total.get()
            if not valor:
                valor = 0
           

            for row in resultado:
                self.tree_servicos.insert('', END, values=row)
                self.entry_valor_total.delete(0, END)
                self.entry_valor_total.config(state=NORMAL)
                try:
                    valor = float(valor)  # Convertendo para float, tratando vírgula como ponto
                except ValueError:
                    print("Coloque um valor válido.") # Se o valor não for um número válido, iniciamos com 0.0

                total = valor + row[1]
                self.entry_valor_total.insert(0, total)
    
    def lista_de_produtos(self):

        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            cursor.execute('SELECT nome_produto FROM produtos')
            produtos = [row[0] for row in cursor.fetchall()]
        self.combobox_produto_atendimento.config(values=produtos)



    def localizar_cliente_atendimento(self, event):
        nome = self.combobox_clientes_atendimento.get()  # Obtém o texto digitado

        # Conexão com o banco de dados
        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()

            # Script SQL para buscar os clientes que correspondem ao texto digitado
            script = '''SELECT nome_cliente FROM clientes WHERE nome_cliente LIKE ?'''
            cursor.execute(script, (f'%{nome}%',)) 

            # Recupera os resultados da consulta
            self.clientes = [row[0] for row in cursor.fetchall()]
            # Fecha a conexão com o banco
            self.combobox_clientes_atendimento.configure(values=self.clientes)
    
    def localizar_cliente(self, event):
        nome = self.combobox_clientes.get()  # Obtém o texto digitado

        # Conexão com o banco de dados
        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()

            # Script SQL para buscar os clientes que correspondem ao texto digitado
            script = '''SELECT nome_cliente FROM clientes WHERE nome_cliente LIKE ?'''
            cursor.execute(script, (f'%{nome}%',)) 

            # Recupera os resultados da consulta
            self.clientes = [row[0] for row in cursor.fetchall()]
            # Fecha a conexão com o banco
            self.combobox_clientes.configure(values=self.clientes)

    
    def localizar_cliente_agendamento(self, event):
        nome = self.combobox_cliente_novo_agendamento.get()

        # Conexão com o banco de dados
        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()

            # Script SQL para buscar os clientes que correspondem ao texto digitado
            script = '''SELECT nome_cliente FROM clientes WHERE nome_cliente LIKE ?'''
            cursor.execute(script, (f'%{nome}%',)) 

            # Recupera os resultados da consulta
            self.clientes = [row[0] for row in cursor.fetchall()]
            # Fecha a conexão com o banco
            self.combobox_cliente_novo_agendamento.configure(values=self.clientes)

    def preencher_atendimento(self,event):
        nome = self.combobox_clientes_atendimento.get()

        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            # Script SQL para buscar os clientes que correspondem ao texto digitado
            script = '''SELECT telefone, email, data_nascimento FROM clientes WHERE nome_cliente = ?'''
            cursor.execute(script, (f'{nome}',)) 

            # Recupera os resultados da consulta
            for row in cursor.fetchall():
                self.data_do_atendimento.entry.config(state=NORMAL)
                self.data_do_atendimento.entry.delete(0, END)
                self.data_do_atendimento.entry.insert(0, row[2])
                self.data_do_atendimento.entry.config(foreground="white")
                self.data_do_atendimento.entry.config(state="disabled")
        
        
    def concluir_atendimento(self):

        confirmacao = messagebox.askquestion("","Tem certeza que deseja concluir o atendimento?")
        if confirmacao == "yes":
            cliente = self.combobox_clientes_atendimento.get()
            data_atendimento = self.data_do_atendimento.entry.get()
            try:
                with sqlite3.connect("barbearia.db") as con:
                    cursor = con.cursor()
                    # Ativa o suporte a chaves estrangeiras
                    cursor.execute("PRAGMA foreign_keys = ON;")

                    # obter id do cliente
                    query_idcliente = '''SELECT id_cliente FROM clientes WHERE nome_cliente = ?'''
                    cursor.execute(query_idcliente,(cliente,))
                    id_cliente = cursor.fetchone()[0]

                    # Busca os itens da Treeview
                    for item in self.tree_servicos.get_children():
                        # Obtém os valores das colunas "SERVIÇOS" e "VALOR DO SERVIÇO"
                        servico = self.tree_servicos.item(item)["values"][0]
                        valor_servico = self.tree_servicos.item(item)["values"][1]
                        # verificar se é produto
                        query_produto = '''SELECT id_servico, tipo_servico
                                        FROM
                                        (SELECT id_servico, tipo_servico from servicos
                                        UNION
                                        SELECT id_produto , nome_produto FROM produtos)
                                        WHERE tipo_servico = ? '''
                        cursor.execute(query_produto,(servico,))
                        for row in cursor.fetchall():
                            id_servico = row[0]
                            tipo_servico = row[1]
                            script = '''INSERT INTO atendimentos (nome_cliente, data_atendimento, descricao_item, valor, id_item, id_cliente)
                                        VALUES (?, ?, ?, ?, ?,?)'''
                            values = (cliente, data_atendimento, tipo_servico, valor_servico, id_servico, id_cliente)
                            cursor.execute(script, values)
                            con.commit()
                    messagebox.showinfo("","Atendimento concluído com sucesso.")
                    

                    # Limpa os campos e reseta os estados
                    self.combobox_clientes_atendimento.delete(0, END)
                    self.data_do_atendimento.entry.config(state=NORMAL)
                    self.data_do_atendimento.entry.delete(0, END)
                    self.data_do_atendimento.entry.config(state=READONLY)
                    self.combobox_servicos.delete(0, END)
                    self.entry_valor_total.delete(0, END)
                    self.combobox_produto_atendimento.delete(0, END)
                    # Limpa os itens da Treeview
                    for item in self.tree_servicos.get_children():
                        self.tree_servicos.delete(item)
            
            except TypeError:
                messagebox.showwarning("Atenção", "Preenchimento inválido.")
            
        elif confirmacao == "no":
            return

    def atualizar_agendamentos_treeview(self):
        df = self.lista_de_agendamentos()
        
        # for item in self.tree_agendamentos.get_children():
        #     self.tree_agendamentos.delete(item)
        
        # for _, item in df.iterrows():
        #     self.tree_agendamentos.insert("", END, values=(item["DATA DE AGENDAMENTO"], item["HORÁRIO DE AGENDAMENTO"], item["NOME DO CLIENTE"], item["TIPO DE SERVIÇO"]))
    

    def lista_de_agendamentos(self):

        df = main()
        df = pd.DataFrame(df[1:], columns=df[0])
        # pd.set_option('display.max_columns', None)
        df["DATA DE AGENDAMENTO"] = pd.to_datetime(df["DATA DE AGENDAMENTO"], dayfirst=True, format='%d/%m/%Y')
        df["DATA DE AGENDAMENTO"] = df["DATA DE AGENDAMENTO"].dt.strftime('%d/%m/%Y')
        df.set_index(df["DATA DE AGENDAMENTO"], inplace=True)
        df.sort_index(inplace=True)
        return df
   
    def buscar_agendamentos(self):
        data = self.data_agendamento.entry.get()
        df = self.lista_de_agendamentos()
        try:
            if data:
                filtro_tree = df.loc[data]
                for item in self.tree_agendamentos.get_children():
                    self.tree_agendamentos.delete(item)
                
                for _, item in filtro_tree.iterrows():
                    self.tree_agendamentos.insert("", END, values=(item["DATA DE AGENDAMENTO"], item["HORÁRIO DE AGENDAMENTO"], item["NOME DO CLIENTE"], item["TIPO DE SERVIÇO"]))
            else:
                self.atualizar_agendamentos_treeview()
        except AttributeError:
            messagebox.showwarning("Atenção", "Nenhum agendamento encontrado.")
        except KeyError:
            messagebox.showwarning("Atenção", "Nenhum agendamento encontrado.")
    

    def criar_novo_agendamento(self):
        cliente = self.combobox_cliente_novo_agendamento.get()
        data = self.entry_datas_agendamento.entry.get()
        horario = self.entry_horario_agendamento.get()
        servico = self.combobox_servicos_novo_agendamento.get()

        if not all([cliente, data, horario, servico]):
            messagebox.showwarning("Atenção", "Preencha todos os campos.")
            return
        
     
        
    def janela_novo_agendamento(self):

        self.janela_agendamento = ttk.Toplevel()
        self.janela_agendamento.title("Novo agendamento")
        self.janela_agendamento.resizable(0,0)
        self.frame_novo_agendamento = ttk.Frame(self.janela_agendamento)
        self.frame_novo_agendamento.pack(padx=20, pady=20)
        self.cliente_novo_agendamento = ttk.Label(self.frame_novo_agendamento, text="Cliente: ")
        self.cliente_novo_agendamento.grid(row=0, column=0, pady=10)
        self.combobox_cliente_novo_agendamento = ttk.Combobox(self.frame_novo_agendamento, width=50, values=[""])
        self.combobox_cliente_novo_agendamento.grid(row=0, column=1)
        self.label_datas = ttk.Label(self.frame_novo_agendamento, text="Data: ")
        self.label_datas.grid(row=1, column=0, pady=10)
        self.entry_datas_agendamento = ttk.DateEntry(self.frame_novo_agendamento,  dateformat="%d/%m/%Y")
        self.entry_datas_agendamento.grid(row=1, column=1)
        self.entry_datas_agendamento.entry.config(font="Arial 12", width=20)
        self.horario_novo_agendamento = ttk.Label(self.frame_novo_agendamento, text="Horário: ")
        self.horario_novo_agendamento.grid(row=2, column=0, pady=10)
        self.entry_horario_agendamento = ttk.Entry(self.frame_novo_agendamento, width=50)
        self.entry_horario_agendamento.grid(row=2, column=1, pady=10)
        self.servicos_novo_agendamento = ttk.Label(self.frame_novo_agendamento, text="Serviço: ")
        self.servicos_novo_agendamento.grid(row=3, column=0, pady=10)
        self.combobox_servicos_novo_agendamento = ttk.Combobox(self.frame_novo_agendamento, values=[""], width=50)
        self.combobox_servicos_novo_agendamento.grid(row=3, column=1, pady=10)
        
        self.frame_agendamento_botoes = ttk.Frame(self.janela_agendamento)
        self.frame_agendamento_botoes.pack()
        self.botao_agendar = ttk.Button(self.frame_agendamento_botoes, text="Agendar", command=None)
        self.botao_agendar.grid(row=0, column=0, pady=10, padx=10)
        self.botao_cancelar_agendamento = ttk.Button(self.frame_agendamento_botoes, text="Cancelar", bootstyle= DANGER, command= lambda: self.janela_agendamento.destroy())
        self.botao_cancelar_agendamento.grid(row=0, column=1, padx=10)

        self.combobox_cliente_novo_agendamento.bind("<KeyRelease>", self.localizar_cliente_agendamento)
        self.lista_de_servicos_agendamento()

    def lembrete_aniversario(self):

        with sqlite3.connect("barbearia.db") as con:
            cursor = con.cursor()
            query = '''SELECT nome_cliente, data_nascimento, email FROM clientes'''
            cursor.execute(query)
            
            # busca a data de hoje
            data_hoje = date.today().strftime("%d/%m")
            
            for row in cursor.fetchall():
                nome_cliente = row[0]
                data_nascimento = datetime.strptime(row[1], "%d/%m/%Y").strftime("%d/%m")

                if data_nascimento == data_hoje:
                    pass

                
    
            
            


  

barbearia()

