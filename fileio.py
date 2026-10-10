"""
fileio.py -- Lecture / ecriture du fichier compresse .rle

STRUCTURE DU FICHIER .rle
-------------------------
  +----------+----------+---------------------------+
  | Largeur  | Hauteur  |  Blocs RLE (donnees)      |
  | 2 octets | 2 octets |  taille variable          |
  +----------+----------+---------------------------+
   <--- en-tete : 4 octets --->

POURQUOI UN EN-TETE ?
Le decodeur recupere seulement une longue suite de pixels (1D).
Sans connaitre la largeur et la hauteur, impossible de la remettre en 2D.
=> C'est une question classique du prof.

POURQUOI BIG-ENDIAN (">HH") ?
">" = big-endian (octet de poids fort en premier), "H" = entier non signe 16 bits.
On garde le MEME ordre qu'au codage des blocs : c'est coherent et lisible
quand on ouvre le fichier dans un editeur hexadecimal.
"""

import os
import struct

import numpy as np

import rle  # notre module coeur (encode / decode)


# Format de l'en-tete : 2 entiers 16 bits en big-endian
FORMAT_ENTETE = ">HH"
TAILLE_ENTETE = struct.calcsize(FORMAT_ENTETE)   # vaut 4


def nettoyer_chemin(chemin):
    """
    Nettoie un chemin saisi au clavier.

    Windows ajoute des guillemets quand on fait
    "Copier en tant que chemin d'acces" dans l'Explorateur :
        "C:\\Users\\...\\dessin.rle"
    Python chercherait alors un fichier dont le nom commence par un guillemet.
    On retire donc les guillemets et les espaces parasites.
    """
    return chemin.strip().strip('"').strip("'").strip()


# ---------------------------------------------------------------------------
# ECRITURE
# ---------------------------------------------------------------------------

def save_rle(chemin, img, trace=False):
    """
    Compresse l'image et l'ecrit dans un fichier .rle

    chemin : nom du fichier de sortie (ex: "sorties/dessin.rle")
    img    : tableau numpy 2D (hauteur, largeur) contenant uniquement 0 et 255
    trace  : affiche le tableau detaille de l'encodage

    Retourne un dictionnaire de statistiques.
    """
    chemin = nettoyer_chemin(chemin)
    hauteur, largeur = img.shape

    # Securite : le compteur de l'en-tete tient sur 16 bits
    if largeur > 65535 or hauteur > 65535:
        raise ValueError("Dimensions trop grandes pour un en-tete 16 bits.")

    # 2D -> 1D : on parcourt l'image ligne par ligne (choix de conception)
    pixels = img.flatten().tolist()

    # Appel du coeur : compression
    donnees = rle.encode(pixels, trace=trace)

    # Ecriture binaire : en-tete puis donnees
    with open(chemin, "wb") as f:
        f.write(struct.pack(FORMAT_ENTETE, largeur, hauteur))
        f.write(donnees)

    taille_originale = largeur * hauteur            # 1 octet par pixel
    taille_compressee = TAILLE_ENTETE + len(donnees)

    return {
        "largeur": largeur,
        "hauteur": hauteur,
        "taille_originale": taille_originale,
        "taille_compressee": taille_compressee,
        "taille_rle_brut": len(donnees),
        "taux": taux_compression(taille_originale, taille_compressee),
    }


# ---------------------------------------------------------------------------
# LECTURE
# ---------------------------------------------------------------------------


def load_rle(chemin, trace=False):
    """
    Lit un fichier .rle, le decompresse et reconstruit l'image 2D.

    Retourne un couple (image numpy 2D, dictionnaire de statistiques).
    """
    chemin = nettoyer_chemin(chemin)

    if not os.path.exists(chemin):
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    with open(chemin, "rb") as f:
        contenu = f.read()

    if len(contenu) < TAILLE_ENTETE:
        raise ValueError("Fichier corrompu : en-tete incomplet (moins de 4 octets).")

    # 1) Lire l'en-tete
    largeur, hauteur = struct.unpack(FORMAT_ENTETE, contenu[:TAILLE_ENTETE])

    if largeur == 0 or hauteur == 0:
        raise ValueError(f"En-tete invalide : dimensions {largeur}x{hauteur}.")

    # 2) Decompresser le reste
    donnees = contenu[TAILLE_ENTETE:]
    pixels = rle.decode(donnees, nb_pixels_attendu=largeur * hauteur, trace=trace)

    # 3) 1D -> 2D : on remet la suite de pixels en tableau (hauteur, largeur)
    img = np.array(pixels, dtype=np.uint8).reshape(hauteur, largeur)

    taille_originale = largeur * hauteur
    taille_compressee = len(contenu)
    stats = {
        "largeur": largeur,
        "hauteur": hauteur,
        "taille_originale": taille_originale,
        "taille_compressee": taille_compressee,
        "taille_rle_brut": len(donnees),
        "taux": taux_compression(taille_originale, taille_compressee),
    }
    return img, stats


# ---------------------------------------------------------------------------
# STATISTIQUES
# ---------------------------------------------------------------------------

def taux_compression(taille_originale, taille_compressee):
    """
    Calcule le taux de compression en pourcentage :
        taux = (1 - taille_compressee / taille_originale) * 100

    - Positif (> 0) : gain de place (compression efficace).
    - Negatif (< 0) : le fichier a GROSSI (cas d'une image bruitee / damier).
    - 0%            : taille inchangee.
    """
    if taille_originale <= 0:
        return 0.0
    return (1.0 - (float(taille_compressee) / float(taille_originale))) * 100.0


def afficher_stats(stats, titre="STATISTIQUES"):
    """Affiche proprement le bilan de compression."""
    print(f"--- {titre} ---")
    print(f"  Dimensions          : {stats['hauteur']} lignes x "
          f"{stats['largeur']} colonnes ({stats['largeur'] * stats['hauteur']} pixels)")
    print(f"  Taille originale    : {stats['taille_originale']} octets (1 octet/pixel)")
    print(f"  Taille fichier .rle : {stats['taille_compressee']} octets "
          f"(dont {TAILLE_ENTETE} d'en-tete)")
    if "taille_rle_brut" in stats:
        print(f"  Donnees RLE pures   : {stats['taille_rle_brut']} octets")

    taux = stats["taux"]
    if taux >= 0:
        print(f"  Taux de compression : {taux:+.2f} %  (gain de place : {taux:.2f} % d'espace gagne)")
    else:
        print(f"  Taux de compression : {taux:+.2f} %  (le fichier a GROSSI : {-taux:.2f} % d'expansion)")
    print()
