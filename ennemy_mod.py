import sqlite3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
import utils_img

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
        
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10, "bold"), padding=5)
        self.style.configure("TLabel", font=("Arial", 12, "bold"), background="#1E1E1E", foreground="white")
        
        self.setup_ui()
        self.charger_liste_ennemis()
        self.charger_ennemis_combat()
    
    def setup_ui(self):
        """Création de l'interface graphique"""
        # Partie gauche : Preview
        self.frame_preview = tk.Frame(self.root, bg="#2C2F33", bd=3, relief=tk.RIDGE)
        self.frame_preview.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        self.liste_ennemis = ttk.Combobox(self.frame_preview, state="readonly")
        self.liste_ennemis.pack()
        self.liste_ennemis.bind("<<ComboboxSelected>>", self.afficher_details_avant_ajout)

        self.bouton_ajouter = ttk.Button(self.frame_preview, text="Ajouter l'ennemi", command=self.ajouter_ennemi)
        self.bouton_ajouter.pack(pady=10)

        self.preview_canvas = tk.Canvas(self.frame_preview, width=220, height=320, bg='#2C2F33', highlightthickness=0)
        self.preview_canvas.pack()
        
        self.ennemis_listbox = tk.Listbox(self.frame_preview, width=40, height=10, bg="#2C2F33", fg="white", font=("Arial", 10, "bold"))
        self.ennemis_listbox.pack(pady=10)
        
        self.frame_battlefield = tk.Frame(self.root, bg="#2C2F33", bd=3, relief=tk.RIDGE)
        self.frame_battlefield.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.battlefield_grid = []

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
        self.cursor.execute("UPDATE ennemis_combat SET pv = pv + ? WHERE numero = ?", (valeur, numero))
        self.conn.commit()
        self.cursor.execute("SELECT pv FROM ennemis_combat WHERE numero = ?", (numero,))
        nouveau_pv = self.cursor.fetchone()[0]
        if nouveau_pv >= 0:
            pv_label.config(text=f"❤️ {nouveau_pv}")
            self.update_health_bar(health_bar, nouveau_pv, max_pv)

    def afficher_carte_sur_battlefield(self, nom, numero):
        """Affiche une carte ennemi sur le battlefield avec un alignement grid et gestion des PV."""
        self.cursor.execute("SELECT mouvement, attaque, pv FROM ennemis_combat WHERE numero = ?", (numero,))
        ennemi = self.cursor.fetchone()
        max_longueur_carte = 150
        max_hauteur_carte = 225
        
        if ennemi:
            mouvement, attaque, pv = ennemi
            max_pv = pv  # Définit le PV initial comme valeur maximale pour la barre de vie
            nom_sans_elite = nom.replace(" ELITE", "")  # Supprime "ELITE" de l'affichage
            
            card_frame = tk.Frame(self.root, bg="#2C2F33", bd=2, relief=tk.RIDGE)
            # Affichage du nom
            card_frame.pack(padx=10, pady=10)
            
            
            card_canvas = tk.Canvas(card_frame, width=max_longueur_carte, height=max_hauteur_carte, bg='#2C2F33', highlightthickness=0)
            card_canvas.pack()
            card_canvas.create_rectangle(5, 5, max_longueur_carte, 295, outline="white", width=2)
            card_canvas.create_text(100, 30, text=nom_sans_elite, font=("Arial", 14, "bold"), fill="white")
            
            pv_label = tk.Label(card_frame, text=f"❤️ {pv}", bg="#2C2F33", fg="red", font=("Arial", 12, "bold"))
            pv_label.pack()
            
            # Charger l'image avec Pillow
            if nom == "Polo":
               image = utils_img.resize_image(Image.open("img/red-guard.png"), max_longueur_carte, max_hauteur_carte)
            else:
               image = utils_img.resize_image(Image.open("img/voidwarden.png"), max_longueur_carte, max_hauteur_carte)     
            photo = ImageTk.PhotoImage(image)
            card_canvas.create_image(max_longueur_carte / 2, max_hauteur_carte / 2, image=photo) # Affichage au centre        
            card_canvas.image = photo
            
            health_bar = tk.Canvas(card_frame, width=100, height=10, bg="#2C2F33", highlightthickness=0)
            health_bar.pack()
            self.update_health_bar(health_bar, pv, max_pv)
            
            button_frame = tk.Frame(card_frame, bg="#2C2F33")
            button_frame.pack(pady=5)
            
            bouton_plus = ttk.Button(button_frame, text="+1", command=lambda: self.modifier_pv(pv_label, health_bar, numero, 1, max_pv), width=4)
            bouton_plus.grid(row=0, column=0, padx=2)
            bouton_moins = ttk.Button(button_frame, text="-1", command=lambda: self.modifier_pv(pv_label, health_bar, numero, -1, max_pv), width=4)
            bouton_moins.grid(row=0, column=1, padx=2)         


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

