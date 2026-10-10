"""
main.py -- Menu CLI du codec RLE.

C'est le point d'entree du projet :
    python main.py

Il ne contient aucune logique de compression : il se contente d'appeler
rle.py (coeur), fileio.py (fichier) et draw.py (dessin/affichage).
"""

import os

import numpy as np

import draw
import fileio
import rle


DOSSIER_SORTIE = "sorties"

# Image courante en memoire, partagee entre les options du menu.
# On la garde dans un dict pour pouvoir la modifier depuis les fonctions.
contexte = {
    "image": None,          # tableau numpy 2D, ou None
    "dernier_rle": None,    # chemin du dernier fichier .rle ecrit
    "dernieres_stats": None, # dictionnaire des dernieres stats de compression
    "mode_texte": False,    # True si OpenCV ne peut pas ouvrir de fenetre
}


# ---------------------------------------------------------------------------
# OPTION 1 : creer une nouvelle image
# ---------------------------------------------------------------------------

def option_nouvelle_image():
    """Demande les dimensions, puis laisse l'utilisateur dessiner."""
    hauteur, largeur = draw.ask_dimensions()

    if contexte["mode_texte"]:
        img = draw.draw_image_texte(hauteur, largeur)
    else:
        img = draw.draw_image(hauteur, largeur)

    if img is None:
        print("Dessin annule.\n")
        return

    # Securite : on force 0/255 avant toute compression
    img = draw.binariser(img)
    contexte["image"] = img

    # Sauvegarde de l'originale en PNG (demande par l'enonce)
    chemin_png = os.path.join(DOSSIER_SORTIE, "originale.png")
    import cv2
    cv2.imwrite(chemin_png, img)

    print(f"Image creee et sauvegardee : {chemin_png}")
    draw.afficher_texte(img, "Apercu ASCII de votre dessin")


# ---------------------------------------------------------------------------
# OPTION 2 : compresser
# ---------------------------------------------------------------------------

def option_compresser():
    """Compresse l'image en memoire vers un fichier .rle, avec la trace."""
    if contexte["image"] is None:
        print("Aucune image en memoire. Utilisez d'abord l'option 1.\n")
        return

    nom = input("Nom du fichier .rle [dessin.rle] : ").strip() or "dessin.rle"
    if not nom.endswith(".rle"):
        nom += ".rle"
    chemin = os.path.join(DOSSIER_SORTIE, nom)

    # trace=True -> affiche le tableau detaille exige par le prof
    stats = fileio.save_rle(chemin, contexte["image"], trace=True)
    contexte["dernieres_stats"] = stats

    fileio.afficher_stats(stats, "COMPRESSION")
    print(f"Fichier ecrit : {chemin}")
    print(f"Taille reelle sur disque : {os.path.getsize(chemin)} octets\n")

    contexte["dernier_rle"] = chemin


# ---------------------------------------------------------------------------
# OPTION 3 : decompresser
# ---------------------------------------------------------------------------

def option_decompresser():
    """Charge un .rle, le decompresse avec la trace, puis affiche l'image."""
    defaut = contexte["dernier_rle"] or os.path.join(DOSSIER_SORTIE, "dessin.rle")
    chemin = input(f"Fichier .rle a charger [{defaut}] : ").strip() or defaut

    try:
        img, stats = fileio.load_rle(chemin, trace=True)
    except (FileNotFoundError, ValueError) as erreur:
        print(f"ERREUR : {erreur}\n")
        return

    contexte["dernieres_stats"] = stats
    fileio.afficher_stats(stats, "DECOMPRESSION")
    draw.afficher_texte(img, "Image reconstruite", stats=stats)

    # Si on a encore l'originale, on verifie que rien n'a ete perdu
    original = contexte["image"]
    if original is not None and original.shape == img.shape:
        identique = np.array_equal(original, img)
        print(f"VERIFICATION : original == decompresse  ->  {identique}")
        if identique:
            print("  => Compression SANS PERTE confirmee.\n")
        else:
            print("  => ATTENTION : difference detectee !\n")

    if not contexte["mode_texte"]:
        if original is not None and original.shape == img.shape:
            draw.show_comparaison(original, img, stats=stats)
        else:
            draw.show(img, "Image decompressee", stats=stats)


# ---------------------------------------------------------------------------
# OPTION 4 : demonstration complete
# ---------------------------------------------------------------------------

def option_demo_complete():
    """Enchaine dessin -> compression -> decompression -> verification."""
    print("\n######## DEMONSTRATION COMPLETE ########")

    option_nouvelle_image()
    if contexte["image"] is None:
        return

    print("\n--- Etape : compression ---")
    chemin = os.path.join(DOSSIER_SORTIE, "demo.rle")
    stats = fileio.save_rle(chemin, contexte["image"], trace=True)
    contexte["dernieres_stats"] = stats
    fileio.afficher_stats(stats, "COMPRESSION")
    contexte["dernier_rle"] = chemin

    print("--- Etape : decompression ---")
    img, stats_decomp = fileio.load_rle(chemin, trace=True)
    fileio.afficher_stats(stats_decomp, "DECOMPRESSION")

    print("--- Etape : verification ---")
    identique = np.array_equal(contexte["image"], img)
    print(f"  original == decompresse : {identique}\n")

    if not contexte["mode_texte"]:
        draw.show_comparaison(contexte["image"], img, stats=stats)
    else:
        draw.afficher_texte(img, "Image decompressee", stats=stats)


# ---------------------------------------------------------------------------
# OPTION 5 : exemple du guide (utile pour la soutenance)
# ---------------------------------------------------------------------------

def option_exemple_guide():
    """Rejoue l'exemple a la main du guide, pour montrer la trace au prof."""
    exemple = [255, 255, 255, 255, 0, 255, 0, 0, 255, 255, 255]

    print("\nExemple du guide (11 pixels) :")
    print("  " + " ".join(f"{p:02X}" for p in exemple))

    donnees = rle.encode(exemple, trace=True)
    print("Octets produits :", " ".join(f"{b:02X}" for b in donnees))
    print("Attendu         : 80 04 FF 00 04 00 FF 00 00 80 03 FF\n")

    retour = rle.decode(donnees, nb_pixels_attendu=len(exemple), trace=True)
    print("Decodage identique a l'original :", retour == exemple)

    taux_ex = fileio.taux_compression(len(exemple), len(donnees))
    print(f"Taille originale    : {len(exemple)} octets")
    print(f"Taille compressee   : {len(donnees)} octets")
    remarque = "gain de place" if taux_ex >= 0 else f"le RLE a grossi (+{-taux_ex:.2f} % d'expansion)"
    print(f"Taux de compression : {taux_ex:+.2f} %  ({remarque})\n")


# ---------------------------------------------------------------------------
# OPTION 6 : charger une image PNG existante
# ---------------------------------------------------------------------------

def option_charger_png():
    """Charge un PNG/JPG, le binarise et le met en memoire."""
    chemin = input("Chemin de l'image a charger : ").strip()
    try:
        img = draw.charger_png(chemin)
    except FileNotFoundError as erreur:
        print(f"ERREUR : {erreur}\n")
        return

    contexte["image"] = img
    print(f"Image chargee et binarisee : {img.shape[0]} x {img.shape[1]}\n")

    if not contexte["mode_texte"]:
        draw.show(img, "Image chargee")


# ---------------------------------------------------------------------------
# MENU PRINCIPAL
# ---------------------------------------------------------------------------

MENU = """
===================================================
          CODEC RLE - IMAGES BINAIRES
   Projet n1 - Communication Multimedia - USTHB
===================================================
  1) Nouvelle image     (choisir n x m, puis dessiner)
  2) Compresser         -> fichier .rle  (trace detaillee)
  3) Decompresser       -> afficher      (trace detaillee)
  4) Demonstration complete (1 + 2 + 3 + verification)
  5) Exemple du guide   (trace de reference)
  6) Charger une image PNG existante
  7) Basculer mode texte / mode fenetre
  0) Quitter
---------------------------------------------------"""


def verifier_opencv():
    """
    Teste si OpenCV peut ouvrir une fenetre.
    Sinon on bascule automatiquement en mode texte.
    """
    try:
        import cv2
        fenetre = np.zeros((1, 1), np.uint8)
        cv2.imshow("__test__", fenetre)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        return True
    except Exception as erreur:
        print(f"[!] Fenetre OpenCV indisponible ({erreur}).")
        print("[!] Bascule automatique en mode texte.\n")
        return False


def main():
    """Boucle principale du menu."""
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)
    contexte["mode_texte"] = not verifier_opencv()

    actions = {
        "1": option_nouvelle_image,
        "2": option_compresser,
        "3": option_decompresser,
        "4": option_demo_complete,
        "5": option_exemple_guide,
        "6": option_charger_png,
    }

    while True:
        print(MENU)
        etat_image = (
            f"{contexte['image'].shape[0]}x{contexte['image'].shape[1]}"
            if contexte["image"] is not None else "aucune"
        )
        mode = "TEXTE" if contexte["mode_texte"] else "FENETRE"
        info_taux = (
            f"  |  dernier taux : {contexte['dernieres_stats']['taux']:+.2f}%"
            if contexte.get("dernieres_stats") else ""
        )
        print(f"  [image en memoire : {etat_image}  |  mode : {mode}{info_taux}]")

        choix = input("Votre choix : ").strip()

        if choix == "0":
            print("Au revoir.")
            break
        elif choix == "7":
            contexte["mode_texte"] = not contexte["mode_texte"]
            print(f"Mode bascule vers : "
                  f"{'TEXTE' if contexte['mode_texte'] else 'FENETRE'}\n")
        elif choix in actions:
            try:
                actions[choix]()
            except Exception as erreur:
                print(f"ERREUR inattendue : {erreur}\n")
        else:
            print("Choix invalide.\n")


if __name__ == "__main__":
    main()
