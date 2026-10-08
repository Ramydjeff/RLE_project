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
    hauteur = demander_entier("Nombre de lignes   (hauteur n) : ", 1, maxi)
    largeur = demander_entier("Nombre de colonnes (largeur  m) : ", 1, maxi)
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


def show(img, titre="Image", zoom=None):
    """Affiche une image zoomee et attend une touche."""
    if zoom is None:
        zoom = calculer_zoom(*img.shape)
    cv2.imshow(titre, agrandir(img, zoom))
    print(f"[{titre}] Appuyez sur une touche dans la fenetre pour continuer...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    cv2.waitKey(1)


def show_comparaison(original, decompresse, zoom=None):
    """
    Affiche l'originale et la decompressee COTE A COTE,
    separees par une bande grise.
    """
    if zoom is None:
        zoom = calculer_zoom(*original.shape)

    gauche = agrandir(original, zoom)
    droite = agrandir(decompresse, zoom)

    # Bande de separation grise de 10 pixels de large
    separation = np.full((gauche.shape[0], 10), 128, dtype=np.uint8)
    combinee = np.hstack([gauche, separation, droite])

    titre = "GAUCHE = originale   |   DROITE = decompressee  (touche pour fermer)"
    cv2.imshow(titre, combinee)
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


def afficher_texte(img, titre="Image"):
    """Affiche l'image dans la console en ASCII (pratique pour le rapport)."""
    hauteur, largeur = img.shape
    print(f"\n--- {titre} ({hauteur}x{largeur}) ---")
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
    img = cv2.imread(chemin, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Impossible de lire l'image : {chemin}")
    return binariser(img)
