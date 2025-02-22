import sqlite3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from ttkbootstrap import Style
from style import configure_style

# Connexion à la base de données SQLite
def connect_db():
    conn = sqlite3.connect("ennemy_mod.db", check_same_thread=False, timeout=10)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout = 5000;")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ennemis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            numero INTEGER NOT NULL,
            mouvement INTEGER NOT NULL,
            attaque INTEGER NOT NULL,
            pv INTEGER NOT NULL,
            etats TEXT DEFAULT '',
            elite INTEGER NOT NULL DEFAULT 0
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ennemis_combat (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            numero INTEGER NOT NULL,
            mouvement INTEGER NOT NULL,
            attaque INTEGER NOT NULL,
            pv INTEGER NOT NULL,
            etats TEXT DEFAULT '',
            elite INTEGER NOT NULL DEFAULT 0
        );
        """)
        cursor.execute("DELETE FROM ennemis_combat")  # Réinitialisation
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='ennemis_combat'")
        conn.commit()
    except sqlite3.OperationalError:
        print("Erreur: La base de données est verrouillée.")
    return conn


class JeuGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestion des Ennemis - Gloomhaven")
        self.root.geometry("1400x700")
        self.root.configure(bg="#1E1E1E")

        self.conn = connect_db()
        self.cursor = self.conn.cursor()

        self.ennemi_selectionne = None

        self.root.protocol("WM_DELETE_WINDOW", self.fermer_connexion)

        # Chargement du style
        self.style = configure_style()

        self.setup_ui()
        self.charger_liste_ennemis()
        self.charger_ennemis_combat()
        
        self.battlefield_grid = []

    
    def setup_ui(self):
        """Création de l'interface graphique"""
        # Partie gauche : Preview
        self.frame_preview = ttk.Frame(self.root, padding=10)
        self.frame_preview.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.liste_ennemis = ttk.Combobox(self.frame_preview, state="readonly")
        self.liste_ennemis.pack()
        self.liste_ennemis.bind("<<ComboboxSelected>>", self.afficher_details_avant_ajout)

        self.bouton_ajouter = ttk.Button(self.frame_preview, text="Ajouter l'ennemi", bootstyle="primary", command=self.ajouter_ennemi)
        self.bouton_ajouter.pack(pady=10)

        self.preview_canvas = tk.Canvas(self.frame_preview, width=220, height=320, bg='#2C2F33', highlightthickness=0)
        self.preview_canvas.pack()

        # Ajout de la liste des ennemis en combat
        self.ennemis_listbox = tk.Listbox(self.frame_preview, font=("Arial", 12), bg="#3C3F41", fg="white", height=10)
        self.ennemis_listbox.pack(fill=tk.X, pady=5)

        # Encadrement du champ de bataille
        self.battlefield_container = ttk.Frame(self.root, padding=10, bootstyle="dark")
        self.battlefield_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)

        self.battlefield_title = ttk.Label(self.battlefield_container, text="CHAMP DE BATAILLE", font=("Arial", 14, "bold"), foreground="white", background="#2C2F33")
        self.battlefield_title.pack(pady=5)

        # Ajout du scrolling
        self.canvas = tk.Canvas(self.battlefield_container, bg="#2C2F33")
        self.scrollbar = ttk.Scrollbar(self.battlefield_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas, padding=10)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)


    def charger_liste_ennemis(self):
        """Charge la liste des ennemis"""
        self.cursor.execute("SELECT nom FROM ennemis ORDER BY nom ASC")
        self.liste_ennemis["values"] = [row[0] for row in self.cursor.fetchall()]
    
    def charger_ennemis_combat(self):
        """Charge et met à jour la liste des ennemis en combat"""
        self.ennemis_listbox.delete(0, tk.END)
        self.cursor.execute("SELECT nom, numero FROM ennemis_combat")
        for nom, numero in self.cursor.fetchall():
            self.ennemis_listbox.insert(tk.END, f"{nom} (#{numero})")
    

    def afficher_details_avant_ajout(self, event):
        """ Affiche une prévisualisation de l'ennemi sans afficher ELITE dans le nom de la carte. """
        selection = self.liste_ennemis.get()

        self.cursor.execute("SELECT nom, mouvement, attaque, pv, elite FROM ennemis WHERE nom = ?", (selection,))
        ennemi = self.cursor.fetchone()

        if ennemi:
            nom, mouvement, attaque, pv, elite = ennemi
            self.preview_canvas.delete("all")  # Efface l'ancienne preview
            self.dessiner_carte(self.preview_canvas, nom.replace(" ELITE", ""), "PREVIEW", mouvement, attaque, pv, elite)  # Suppression de #PREVIEW du rendu visuel


    def afficher_details_ennemi(self, event):
        """ Affiche les détails d'un ennemi sélectionné dans la liste des ennemis en combat. """
        selection = self.ennemis_listbox.curselection()
        if not selection:
            return

        index = selection[0]
        self.cursor.execute("SELECT nom, numero, mouvement, attaque, pv, elite FROM ennemis_combat LIMIT 1 OFFSET ?", (index,))
        ennemi = self.cursor.fetchone()

        if ennemi:
            nom, numero, mouvement, attaque, pv, elite = ennemi
            print(f"Ennemi sélectionné : {nom}, Mvt: {mouvement}, Atk: {attaque}, PV: {pv}")

            # Déterminer le prochain numéro unique dans ennemis_combat
            self.cursor.execute("SELECT COALESCE(MAX(numero), 0) + 1 FROM ennemis_combat")
            prochain_numero = self.cursor.fetchone()[0]

            self.cursor.execute("""
                INSERT INTO ennemis_combat (nom, numero, mouvement, attaque, pv, etats, elite)
                SELECT ?, ?, mouvement, attaque, pv, etats, elite FROM ennemis WHERE nom = ?
            """, (nom, prochain_numero, nom))

            self.conn.commit()

            # Affichage de la carte sur le battlefield
            self.afficher_carte_sur_battlefield(nom, prochain_numero)

    def update_health_bar(self, canvas, pv, max_pv):
        """Met à jour la barre de PV avec un dégradé dynamique en fonction du max des PV."""
        canvas.delete("all")
        if pv <= 0:
            canvas.create_rectangle(0, 0, 0, 10, fill=f"#000000", outline=f"#000000")
        else:
            percentage = max(0, min(1, pv / max_pv))  # Assure que le ratio est entre 0 et 1
            red = int((1 - percentage) * 255)
            green = int(percentage * 255)
            color = f"#{red:02X}{green:02X}00"
            canvas.create_rectangle(0, 0, int(100 * percentage), 10, fill=color, outline=color)
    
    def modifier_pv(self, pv_label, health_bar, numero, valeur, max_pv):
        """Modifie les points de vie d'un ennemi et met à jour l'affichage."""
        self.cursor.execute("UPDATE ennemis_combat SET pv = MAX(0, pv + ?) WHERE numero = ?", (valeur, numero))
        self.conn.commit()
        self.cursor.execute("SELECT pv FROM ennemis_combat WHERE numero = ?", (numero,))
        nouveau_pv = self.cursor.fetchone()[0]
        if nouveau_pv >= 0:
            pv_label.config(text=f"❤️ {nouveau_pv}")
            self.update_health_bar(health_bar, nouveau_pv, max_pv)
    
    def afficher_carte_sur_battlefield(self, nom, numero):
        """Affiche une carte ennemi sur le battlefield avec un alignement grid et gestion des PV."""
        self.cursor.execute("SELECT mouvement, attaque, pv, elite FROM ennemis_combat WHERE numero = ?", (numero,))
        ennemi = self.cursor.fetchone()

        if ennemi:
            mouvement, attaque, pv, elite = ennemi
            max_pv = pv  # PV maximum initial
            nom_sans_elite = nom.replace(" ELITE", "")

            row = len(self.battlefield_grid) // 3
            col = len(self.battlefield_grid) % 3

            # Création du cadre pour la carte
            card_frame = ttk.Frame(self.scrollable_frame, padding=10, bootstyle="dark")
            card_frame.grid(row=row, column=col, padx=10, pady=10)

            # Création du canvas pour le rendu visuel de la carte
            card_canvas = tk.Canvas(card_frame, width=200, height=250, bg='#2C2F33', highlightthickness=0)
            card_canvas.pack()
            card_canvas.create_rectangle(5, 5, 195, 245, outline="white", width=2)

            # Affichage du nom et ID
            card_canvas.create_text(100, 30, text=nom_sans_elite, font=("Arial", 14, "bold"), fill="white")
            if elite == 1:
                card_canvas.create_text(100, 50, text="ELITE", font=("Arial", 12, "bold"), fill="gold")
            card_canvas.create_text(100, 70, text=f"#{numero}", font=("Arial", 12, "bold"), fill="white")

            # Affichage des statistiques (mouvement et attaque en bas de la carte)
            card_canvas.create_text(50, 210, text=f"🏃 {mouvement}", font=("Arial", 14, "bold"), fill="white")
            card_canvas.create_text(150, 210, text=f"⚔️ {attaque}", font=("Arial", 14, "bold"), fill="white")

            # Affichage des PV
            pv_label = ttk.Label(card_frame, text=f"❤️ {pv}", bootstyle="danger", font=("Arial", 12, "bold"))
            pv_label.pack()

            # Affichage de la barre de vie
            health_bar = tk.Canvas(card_frame, width=100, height=10, bg="#2C2F33", highlightthickness=0)
            health_bar.pack()
            self.update_health_bar(health_bar, pv, max_pv)

            # Ajout des boutons de gestion des PV
            button_frame = ttk.Frame(card_frame, padding=5)
            button_frame.pack()

            # Bouton -1 (PV)
            bouton_moins = ttk.Button(button_frame, text="-1", bootstyle="danger", command=lambda: self.modifier_pv(pv_label, health_bar, numero, -1, max_pv), width=4)
            bouton_moins.grid(row=0, column=0, padx=2)

            # Bouton +1 (PV)
            bouton_plus = ttk.Button(button_frame, text="+1", bootstyle="success", command=lambda: self.modifier_pv(pv_label, health_bar, numero, 1, max_pv), width=4)
            bouton_plus.grid(row=0, column=1, padx=2)

            # Bouton "Mort" pour supprimer la carte
            bouton_mort = ttk.Button(button_frame, text="Mort", bootstyle="secondary", command=lambda: self.supprimer_ennemi(card_frame, numero), width=6)
            bouton_mort.grid(row=0, column=2, padx=2)

            self.battlefield_grid.append(card_frame)

            

    def dessiner_carte(self, canvas, nom, numero, mouvement, attaque, pv, elite):
        """ Dessine une carte avec indication ELITE si applicable et nom sans ELITE. """
        canvas.delete("all")

        # Retirer " ELITE" du nom affiché sur la carte
        nom_sans_elite = nom.replace(" ELITE", "")

        # Dessiner la carte
        canvas.create_rectangle(5, 5, 195, 295, outline="white", width=2)

        # Affichage du nom
        canvas.create_text(100, 30, text=nom_sans_elite, font=("Arial", 14, "bold"), fill="white")

        # Affichage du statut ELITE si applicable
        if elite == 1:
            canvas.create_text(100, 50, text="ELITE", font=("Arial", 12, "bold"), fill="gold")

        # Affichage du numéro unique sous "ELITE" ou sous le nom si non Elite
        if numero != "PREVIEW":
            canvas.create_text(100, 70 if elite == 1 else 50, text=f"#{numero}", font=("Arial", 12, "bold"), fill="white")

        # Affichage des statistiques
        canvas.create_text(50, 150, text=f"🏃 {mouvement}", font=("Arial", 12, "bold"), fill="white")
        canvas.create_text(50, 170, text=f"⚔️ {attaque}", font=("Arial", 12, "bold"), fill="white")
        canvas.create_text(50, 190, text=f"❤️ {pv}", font=("Arial", 12, "bold"), fill="red")
    

    def ajouter_ennemi(self):
        """Ajoute un ennemi et met à jour la liste"""
        selection = self.liste_ennemis.get()
        if not selection:
            return
        self.cursor.execute("SELECT COALESCE(MAX(numero), 0) + 1 FROM ennemis_combat")
        prochain_numero = self.cursor.fetchone()[0]
        
        self.cursor.execute("""
            INSERT INTO ennemis_combat (nom, numero, mouvement, attaque, pv, etats, elite)
            SELECT ?, ?, mouvement, attaque, pv, etats, elite FROM ennemis WHERE nom = ?
        """, (selection, prochain_numero, selection))
        self.conn.commit()
        
        self.charger_ennemis_combat()
        self.afficher_carte_sur_battlefield(selection, prochain_numero)

    def supprimer_ennemi(self, card_frame, numero):
        """ Supprime un ennemi du champ de bataille et de la base de données """
        card_frame.destroy()  # Supprime la carte de l'interface

        # Supprime l'ennemi de la base de données
        self.cursor.execute("DELETE FROM ennemis_combat WHERE numero = ?", (numero,))
        self.conn.commit()

        # Met à jour la liste des ennemis en combat et le field sous la preview
        self.charger_ennemis_combat()

    def fermer_connexion(self):
        """Fermeture propre de la base de données"""
        self.cursor.execute("DELETE FROM ennemis_combat")
        self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='ennemis_combat'")
        self.conn.commit()
        self.conn.close()
        self.root.destroy()

# Lancer l'interface
tk_root = tk.Tk()
app = JeuGUI(tk_root)
tk_root.mainloop()

