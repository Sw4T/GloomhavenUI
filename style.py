from ttkbootstrap import Style

def configure_style():
    style = Style(theme="darkly")

    # Configuration des boutons
    style.configure("TButton", font=("Arial", 10, "bold"), padding=5)

    # Configuration des labels
    style.configure("TLabel", font=("Arial", 12, "bold"), background="#2C2F33", foreground="white")

    # Configuration des cadres
    style.configure("TFrame", background="#2C2F33", padding=10)

    return style
