    def criar_layout(self):
        """Monta a estrutura visual da tabela, relógio, indicador e gráfico."""
        topo_frame = tk.Frame(self.root, bg="#1e1e1e")
        topo_frame.pack(padx=20, pady=10, fill=tk.X)

        # --- LINHA 1: TÍTULO PRINCIPAL ---
        linha1_frame = tk.Frame(topo_frame, bg="#1e1e1e")
        linha1_frame.pack(fill=tk.X, side=tk.TOP)

        lbl_titulo = tk.Label(
            linha1_frame, 
            text="MONITORAMENTO EM TEMPO REAL", 
            font=self.fonte_titulo, fg="#00ff66", bg="#1e1e1e"
        )
        lbl_titulo.pack(side=tk.LEFT, pady=(0, 5))

        # --- LINHA 2: IP DO CLP E STATUS DA COMUNICAÇÃO ---
        linha2_frame = tk.Frame(topo_frame, bg="#1e1e1e")
        linha2_frame.pack(fill=tk.X, side=tk.TOP, pady=(5, 0))

        lbl_ip = tk.Label(
            linha2_frame, 
            text=f"CLP IP: {IP_CLP}", 
            font=self.fonte_cabecalho, fg="#9cdcfe", bg="#1e1e1e"
        )
        lbl_ip.pack(side=tk.LEFT)

        self.canvas_led = tk.Canvas(linha2_frame, width=25, height=25, bg="#1e1e1e", bd=0, highlightthickness=0)
        self.canvas_led.pack(side=tk.RIGHT, padx=(5, 0))
        self.led_id = self.canvas_led.create_oval(3, 3, 22, 22, fill="#444444", outline="#666666")

        lbl_led_texto = tk.Label(linha2_frame, text="COM:", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e")
        lbl_led_texto.pack(side=tk.RIGHT)

        # ----------------------------------------------------------------------
        # PAINEL DO RELÓGIO DIGITAL UNIFICADO
        # ----------------------------------------------------------------------
        frame_relogio = tk.LabelFrame(self.root, text=" HORÁRIO DO CLP ", font=self.fonte_cabecalho, fg="#ffffff", bg="#151515", bd=2, relief=tk.GROOVE)
        frame_relogio.pack(padx=20, pady=5, fill=tk.X)

        self.lbl_relogio_hora = tk.Label(frame_relogio, text="--:--:--", font=self.fonte_lcd_grande, fg="#00ffff", bg="#151515")
        self.lbl_relogio_hora.pack(pady=2)

        self.lbl_relogio_data = tk.Label(frame_relogio, text="DATA: --/--/----", font=self.fonte_dados, fg="#888888", bg="#151515")
        self.lbl_relogio_data.pack(pady=2)

        # ----------------------------------------------------------------------
        # PAINEL DAS VARIÁVEIS (TABELA DINÂMICA)
        # ----------------------------------------------------------------------
        frame_tabela = tk.LabelFrame(self.root, text=" VARIÁVEIS DE PROCESSO ", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e", bd=0)
        frame_tabela.pack(padx=20, pady=5, fill=tk.X)

        frame_tabela.columnconfigure(0, weight=2)
        frame_tabela.columnconfigure(1, weight=1)
        frame_tabela.columnconfigure(2, weight=1)

        cabecalhos = ["TagName", "Value", "Status"]
        for col_idx, texto in enumerate(cabecalhos):
            lbl = tk.Label(
                frame_tabela, text=texto, font=self.fonte_cabecalho, 
                fg="#ffffff", bg="#2d2d2d", relief=tk.FLAT
            )
            lbl.grid(row=0, column=col_idx, sticky="nsew", padx=1, pady=2, ipady=4)

        tags_exibicao = ['Conta[0].acc', 'Conta[1].acc'] + [f'Reais[{i}]' for i in range(6)]
        
        for row_idx, tag in enumerate(tags_exibicao, start=1):
            cor_fundo = "#252526" if row_idx % 2 == 0 else "#2d2d2d"

            lbl_name = tk.Label(frame_tabela, text=tag, font=self.fonte_dados, fg="#9cdcfe", bg=cor_fundo, anchor="w")
            lbl_name.grid(row=row_idx, column=0, sticky="nsew", padx=1, pady=1, ipadx=5, ipady=4)

            cor_valores = "#00ffff" if "Reais" in tag else "#ff9900"
            lbl_value = tk.Label(frame_tabela, text="---", font=self.fonte_lcd_media, fg=cor_valores, bg=cor_fundo, anchor="center")
            lbl_value.grid(row=row_idx, column=1, sticky="nsew", padx=1, pady=1)

            lbl_status = tk.Label(frame_tabela, text="---", font=self.fonte_dados, fg="#ce9178", bg=cor_fundo, anchor="center")
            lbl_status.grid(row=row_idx, column=2, sticky="nsew", padx=1, pady=1)

            self.widgets_dados[tag.lower()] = {
                "value_widget": lbl_value,
                "status_widget": lbl_status
            }

        # ----------------------------------------------------------------------
        # PAINEL DO HISTÓRICO GRÁFICO (Canvas Real-Time Multitendência)
        # ----------------------------------------------------------------------
        frame_grafico = tk.LabelFrame(self.root, text=" TENDÊNCIA EM TEMPO REAL ( Laranja: Conta[0].acc | Ciano: Segundos ) ", font=self.fonte_cabecalho, fg="#ffffff", bg="#1e1e1e", bd=1, relief=tk.SOLID)
        frame_grafico.pack(padx=20, pady=1)
