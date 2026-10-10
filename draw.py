"""
draw.py -- Saisie des dimensions, dessin a la souris, affichage.

C'est la seule partie qui utilise OpenCV (cv2).
Ce n'est PAS une GUI au sens strict : c'est une simple fenetre imshow
avec un callback souris. La consigne du prof (CLI suffit) est respectee.

CONVENTION IMPORTANTE
---------------------
  Image numpy = tableau (hauteur, largeur) = (lignes, colonnes)
  Souris OpenCV = coordonnees (x, y) = (colonne, ligne)
  => Il faut donc inverser : ligne = y, colonne = x. Piege classique.

  Pixel NOIR  = 0
  Pixel BLANC = 255
"""

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# 1) DEMANDER LES DIMENSIONS A L'UTILISATEUR
# ---------------------------------------------------------------------------

def ask_dimensions(maxi=512):
    """
    Demande n (hauteur) et m (largeur) en boucle jusqu'a saisie valide.
    Retourne un couple (hauteur, largeur).
    """
    print("\n--- Dimensions de l'image ---")
    hauteur = demander_entier("Nombre de lignes n : ", 1, maxi)
    largeur = demander_entier("Nombre de colonnes m : ", 1, maxi)
    print(f"Image de {hauteur} x {largeur} = {hauteur * largeur} pixels.\n")
    return hauteur, largeur


def demander_entier(message, mini, maxi):
    """Lit un entier au clavier, en redemandant tant que c'est invalide."""
    while True:
        saisie = input(message).strip()
        try:
            valeur = int(saisie)
        except ValueError:
            print(f"  -> '{saisie}' n'est pas un entier. Reessayez.")
            continue

        if not (mini <= valeur <= maxi):
            print(f"  -> La valeur doit etre entre {mini} et {maxi}.")
            continue

        return valeur


def calculer_zoom(hauteur, largeur, cible=600, zoom_max=40):
    """
    Choisit automatiquement un facteur de zoom pour que la fenetre
    fasse environ 'cible' pixels de cote (une image 10x10 serait
    invisible autrement).
    """
    zoom = min(cible // max(hauteur, largeur), zoom_max)
    return max(zoom, 1)   # jamais en dessous de 1


# ---------------------------------------------------------------------------
# 2) DESSINER A LA SOURIS
# ---------------------------------------------------------------------------

def draw_image(hauteur, largeur, zoom=None):
    """
    Ouvre une fenetre ou l'utilisateur dessine son image binaire.

    COMMANDES :
      clic gauche  (maintenu) = peindre en NOIR
      clic droit   (maintenu) = gommer en BLANC
      s = valider et continuer
      r = tout effacer
      i = inverser les couleurs
      q = annuler

    Retourne le tableau numpy (hauteur, largeur), ou None si annule.
    """
    if zoom is None:
        zoom = calculer_zoom(hauteur, largeur)

    # Image de depart : toute blanche
    img = np.full((hauteur, largeur), 255, dtype=np.uint8)

    # Dictionnaire d'etat partage avec le callback souris.
    # (On utilise un dict plutot que "global" : plus propre.)
    etat = {"bouton": None}   # None, "noir" ou "blanc"

    def peindre(x, y, couleur):
        """Convertit les coordonnees ecran -> pixel image, puis peint."""
        ligne = y // zoom        # y = vertical   -> ligne
        colonne = x // zoom      # x = horizontal -> colonne
        if 0 <= ligne < hauteur and 0 <= colonne < largeur:
            img[ligne, colonne] = couleur

    def on_mouse(event, x, y, flags, param):
        # Appui sur un bouton : on memorise la couleur et on peint tout de suite
        if event == cv2.EVENT_LBUTTONDOWN:
            etat["bouton"] = 0        # noir
            peindre(x, y, 0)
        elif event == cv2.EVENT_RBUTTONDOWN:
            etat["bouton"] = 255      # blanc (gomme)
            peindre(x, y, 255)

        # Relachement : on arrete de peindre
        elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
            etat["bouton"] = None

        # Deplacement avec un bouton enfonce : trace continu
        elif event == cv2.EVENT_MOUSEMOVE and etat["bouton"] is not None:
            peindre(x, y, etat["bouton"])

    titre = "Dessin  (clic G = noir, clic D = gomme | s=valider r=reset i=inverser q=quitter)"
    cv2.namedWindow(titre)
    cv2.setMouseCallback(titre, on_mouse)

    print("Fenetre de dessin ouverte.")
    print("  clic gauche = noir | clic droit = gomme")
    print("  s = valider   r = effacer   i = inverser   q = annuler")

    resultat = None
    while True:
        cv2.imshow(titre, agrandir(img, zoom))

        touche = cv2.waitKey(20) & 0xFF

        if touche == ord("s"):
            resultat = img
            break
        elif touche == ord("r"):
            img[:] = 255
        elif touche == ord("i"):
            img[:] = 255 - img       # 0 <-> 255
        elif touche == ord("q"):
            resultat = None
            break

    cv2.destroyAllWindows()
    cv2.waitKey(1)   # laisse le temps a la fenetre de se fermer (bug Windows)
    return resultat


# ---------------------------------------------------------------------------
# 3) AFFICHAGE
# ---------------------------------------------------------------------------

def agrandir(img, zoom):
    """
    Agrandit l'image SANS FLOU.

    INTER_NEAREST = chaque pixel devient un gros carre net.
    (Avec l'interpolation par defaut, les pixels seraient flous
     et on ne verrait plus la grille.)
    """
    if zoom <= 1:
        return img
    return cv2.resize(img, None, fx=zoom, fy=zoom,
                      interpolation=cv2.INTER_NEAREST)


def ajouter_bandeau_info(image_bgr, stats=None):
    """
    Ajoute un bandeau informatif elegant en bas de l'image (OpenCV BGR).
    Affiche les dimensions, tailles en octets et le taux de compression.
    """
    if stats is None:
        return image_bgr

    largeur_img = image_bgr.shape[1]
    h_bandeau = 60
    bandeau = np.full((h_bandeau, largeur_img, 3), (30, 30, 30), dtype=np.uint8)

    # Ligne de separation gris clair
    cv2.line(bandeau, (0, 0), (largeur_img, 0), (70, 70, 70), 1)

    taille_orig = stats.get("taille_originale", 0)
    taille_comp = stats.get("taille_compressee", 0)
    taux = stats.get("taux", 0.0)

    ligne1 = f"Originale: {taille_orig} octets  |  Compressee: {taille_comp} octets"
    remarque = "Gain de place" if taux >= 0 else "Fichier grossi"
    ligne2 = f"Taux de compression: {taux:+.2f} %  ({remarque})"

    # Couleur du taux : vert si gain, orange/rouge si grossi
    couleur_taux = (80, 220, 80) if taux >= 0 else (60, 100, 255)

    # Echelle de police adaptee
    scale = max(0.42, min(0.65, largeur_img / 600.0))
    epaisseur = 1

    cv2.putText(bandeau, ligne1, (15, 22), cv2.FONT_HERSHEY_SIMPLEX, scale, (220, 220, 220), epaisseur, cv2.LINE_AA)
    cv2.putText(bandeau, ligne2, (15, 48), cv2.FONT_HERSHEY_SIMPLEX, scale, couleur_taux, epaisseur + 1, cv2.LINE_AA)

    return np.vstack([image_bgr, bandeau])


def show(img, titre="Image", zoom=None, stats=None):
    """Affiche une image zoomee avec bandeau de stats optionnel et attend une touche."""
    if zoom is None:
        zoom = calculer_zoom(*img.shape)

    vue = agrandir(img, zoom)
    vue_bgr = cv2.cvtColor(vue, cv2.COLOR_GRAY2BGR)

    if stats is not None and "taux" in stats:
        vue_bgr = ajouter_bandeau_info(vue_bgr, stats)
        titre_fenetre = f"{titre} | Taux: {stats['taux']:+.2f}%  (touche pour fermer)"
    else:
        titre_fenetre = f"{titre}  (touche pour fermer)"

    cv2.imshow(titre_fenetre, vue_bgr)
    print(f"[{titre}] Appuyez sur une touche dans la fenetre pour continuer...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.waitKey(1)


def show_comparaison(original, decompresse, zoom=None, stats=None):
    """
    Affiche l'originale et la decompressee COTE A COTE,
    separees par une bande grise, avec le taux de compression
    dans le titre et dans un bandeau d'information.
    """
    if zoom is None:
        zoom = calculer_zoom(*original.shape)

    gauche = agrandir(original, zoom)
    droite = agrandir(decompresse, zoom)

    # Bande de separation grise de 10 pixels de large
    separation = np.full((gauche.shape[0], 10), 128, dtype=np.uint8)
    combinee = np.hstack([gauche, separation, droite])
    combinee_bgr = cv2.cvtColor(combinee, cv2.COLOR_GRAY2BGR)

    if stats is not None and "taux" in stats:
        combinee_bgr = ajouter_bandeau_info(combinee_bgr, stats)
        taille_orig = stats.get("taille_originale", original.size)
        taille_comp = stats.get("taille_compressee", 0)
        titre = (f"Originale ({taille_orig} o) vs Decompressee ({taille_comp} o) | "
                 f"Taux: {stats['taux']:+.2f}%  (touche pour fermer)")
    else:
        titre = "GAUCHE = originale   |   DROITE = decompressee  (touche pour fermer)"

    cv2.imshow(titre, combinee_bgr)
    print("Comparaison affichee. Appuyez sur une touche dans la fenetre...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.waitKey(1)


# ---------------------------------------------------------------------------
# 4) MODE TEXTE DE SECOURS (si OpenCV ne peut pas ouvrir de fenetre)
# ---------------------------------------------------------------------------

def draw_image_texte(hauteur, largeur):
    """
    Saisie de l'image au clavier, ligne par ligne.
      '#' = pixel noir      '.' (ou espace) = pixel blanc

    Utile si la fenetre OpenCV ne s'ouvre pas (machine sans affichage).
    """
    print(f"\nSaisissez {hauteur} lignes de {largeur} caracteres.")
    print("  '#' = noir   '.' = blanc   (une ligne trop courte est "
          "completee en blanc)\n")

    img = np.full((hauteur, largeur), 255, dtype=np.uint8)

    for ligne in range(hauteur):
        saisie = input(f"  ligne {ligne + 1:>3}/{hauteur} : ")
        for colonne in range(min(largeur, len(saisie))):
            if saisie[colonne] == "#":
                img[ligne, colonne] = 0

    return img


def afficher_texte(img, titre="Image", stats=None):
    """Affiche l'image dans la console en ASCII (pratique pour le rapport)."""
    hauteur, largeur = img.shape
    print(f"\n--- {titre} ({hauteur}x{largeur}) ---")
    if stats is not None and "taux" in stats:
        print(f"  [Taille : {stats['taille_originale']} o -> {stats['taille_compressee']} o "
              f" | Taux : {stats['taux']:+.2f}%]")
    for ligne in range(hauteur):
        print("  " + "".join("#" if img[ligne, c] == 0 else "."
                             for c in range(largeur)))
    print()


# ---------------------------------------------------------------------------
# 5) UTILITAIRES
# ---------------------------------------------------------------------------

def binariser(img):
    """
    Force l'image a ne contenir QUE 0 et 255.
    Indispensable avant l'encodage : une valeur comme 128 casserait
    l'hypothese "image binaire" du projet.
    """
    _, binaire = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
    return binaire


def charger_png(chemin):
    """Charge une image PNG/JPG en niveaux de gris, puis la binarise."""
    # Meme nettoyage que pour les .rle : Windows colle des guillemets
    # autour du chemin quand on fait "Copier en tant que chemin d'acces".
    chemin = chemin.strip().strip('"').strip("'").strip()

    img = cv2.imread(chemin, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Impossible de lire l'image : {chemin}")
    return binariser(img)
