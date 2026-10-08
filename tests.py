"""
tests.py -- Tests automatiques du codec.

Lancer :  python tests.py

Couvre tous les cas du jeu de tests du guide (section 11) :
image uniforme, damier, runs > 32767, bords, image 1x1, etc.
"""

import os
import random

import numpy as np

import fileio
import rle


# Compteurs globaux
reussis = 0
echoues = 0


def verifier(condition, nom, detail=""):
    """Petit assert maison qui affiche OK / ECHEC au lieu de planter."""
    global reussis, echoues
    if condition:
        reussis += 1
        print(f"  [OK]    {nom}")
    else:
        echoues += 1
        print(f"  [ECHEC] {nom}   {detail}")


def aller_retour(pixels, nom):
    """Verifie que decode(encode(x)) == x."""
    donnees = rle.encode(pixels)
    retour = rle.decode(donnees, nb_pixels_attendu=len(pixels))
    verifier(retour == list(pixels), nom,
             f"({len(pixels)} pixels -> {len(donnees)} octets)")
    return donnees


# ---------------------------------------------------------------------------
def test_exemple_guide():
    print("\n[1] Exemple de reference du guide")
    exemple = [255, 255, 255, 255, 0, 255, 0, 0, 255, 255, 255]
    attendu = bytes([0x80, 0x04, 0xFF,
                     0x00, 0x04, 0x00, 0xFF, 0x00, 0x00,
                     0x80, 0x03, 0xFF])
    obtenu = rle.encode(exemple)
    verifier(obtenu == attendu, "octets exactement conformes au guide",
             f"obtenu={obtenu.hex(' ')}")
    aller_retour(exemple, "aller-retour de l'exemple")


def test_cas_simples():
    print("\n[2] Cas simples et bords")
    aller_retour([255], "image 1x1 (un seul pixel)")
    aller_retour([0], "un seul pixel noir")
    aller_retour([0, 255], "deux pixels differents")
    aller_retour([0, 0], "deux pixels identiques (reste litteral)")
    aller_retour([0, 0, 0], "exactement 3 identiques (devient repetition)")
    aller_retour([255] * 1000, "1000 pixels blancs")

    # Verification du cout : 1000 blancs doivent tenir en 3 octets
    donnees = rle.encode([255] * 1000)
    verifier(donnees == bytes([0x83, 0xE8, 0xFF]),
             "1000 blancs -> 3 octets (83 E8 FF)", donnees.hex(' '))


def test_frontieres():
    print("\n[3] Frontieres litteral / repetition")
    aller_retour([0, 0, 255, 255, 255], "00 00 puis FF FF FF")
    aller_retour([0, 0, 0, 255, 0, 0], "00x3 puis FF puis 00 00")
    aller_retour([255, 0, 255, 0, 255], "alternance (pire cas)")
    aller_retour([0, 0, 0, 255], "repetition puis pixel isole a la fin")
    aller_retour([255, 0, 0, 0], "pixel isole au debut")

    # Le damier doit faire GROSSIR les donnees
    damier = [255 if i % 2 == 0 else 0 for i in range(100)]
    donnees = aller_retour(damier, "damier 100 pixels")
    verifier(len(donnees) > 100, "le damier agrandit bien les donnees",
             f"{len(donnees)} octets pour 100 pixels")


def test_limite_15_bits():
    print("\n[4] Limite des 15 bits (32767)")
    aller_retour([0] * 32767, "exactement 32767 (un seul bloc)")

    donnees = rle.encode([0] * 32767)
    verifier(len(donnees) == 3, "32767 tient en 1 bloc de 3 octets",
             f"{len(donnees)} octets")

    aller_retour([0] * 32768, "32768 (decoupage en 2 blocs)")
    donnees = rle.encode([0] * 32768)
    verifier(len(donnees) == 6, "32768 -> 2 blocs = 6 octets",
             f"{len(donnees)} octets")

    aller_retour([255] * 40000, "run de 40000 pixels")


def test_aleatoire():
    print("\n[5] 200 listes aleatoires")
    random.seed(42)   # graine fixe = tests reproductibles
    toutes_ok = True

    for _ in range(200):
        taille = random.randint(1, 500)
        # On melange des zones unies et du bruit pour varier les cas
        pixels = []
        while len(pixels) < taille:
            if random.random() < 0.5:
                pixels.extend([random.choice([0, 255])] * random.randint(1, 20))
            else:
                pixels.extend(random.choice([0, 255]) for _ in range(random.randint(1, 10)))
        pixels = pixels[:taille]

        donnees = rle.encode(pixels)
        if rle.decode(donnees, nb_pixels_attendu=taille) != pixels:
            toutes_ok = False
            break

    verifier(toutes_ok, "decode(encode(x)) == x sur 200 listes aleatoires")


def test_fichier():
    print("\n[6] Fichier .rle (ecriture / lecture)")
    os.makedirs("sorties", exist_ok=True)
    chemin = os.path.join("sorties", "_test.rle")

    cas = [
        ("image toute blanche 20x20", np.full((20, 20), 255, np.uint8)),
        ("image toute noire 20x20", np.zeros((20, 20), np.uint8)),
        ("image 1x1", np.array([[0]], np.uint8)),
        ("image 1 x m (une ligne)", np.full((1, 50), 255, np.uint8)),
        ("image n x 1 (une colonne)", np.full((50, 1), 0, np.uint8)),
    ]

    # Damier : le pire cas
    damier = np.indices((16, 16)).sum(axis=0) % 2 * 255
    cas.append(("damier 16x16", damier.astype(np.uint8)))

    # Carre noir sur fond blanc : le meilleur cas realiste
    carre = np.full((32, 32), 255, np.uint8)
    carre[8:24, 8:24] = 0
    cas.append(("carre noir 32x32", carre))

    for nom, img in cas:
        stats = fileio.save_rle(chemin, img)
        relue, _ = fileio.load_rle(chemin)
        verifier(np.array_equal(img, relue), nom,
                 f"taux = {stats['taux']:.1f} %")

    os.remove(chemin)


def test_erreurs():
    print("\n[7] Gestion des erreurs")

    def attend_erreur(fonction, nom):
        try:
            fonction()
            verifier(False, nom, "aucune erreur levee")
        except (ValueError, FileNotFoundError):
            verifier(True, nom)

    attend_erreur(lambda: fileio.load_rle("sorties/_inexistant.rle"),
                  "fichier absent detecte")

    attend_erreur(lambda: rle.decode(bytes([0x80])),
                  "mot de controle incomplet detecte")

    attend_erreur(lambda: rle.decode(bytes([0x80, 0x05])),
                  "couleur manquante detectee")

    attend_erreur(lambda: rle.decode(bytes([0x00, 0x05, 0xFF])),
                  "donnees litterales tronquees detectees")

    attend_erreur(lambda: rle.decode(bytes([0x80, 0x04, 0xFF]), nb_pixels_attendu=99),
                  "nombre de pixels incoherent detecte")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 60)
    print("           TESTS AUTOMATIQUES DU CODEC RLE")
    print("=" * 60)

    test_exemple_guide()
    test_cas_simples()
    test_frontieres()
    test_limite_15_bits()
    test_aleatoire()
    test_fichier()
    test_erreurs()

    print("\n" + "=" * 60)
    print(f"  RESULTAT : {reussis} reussis, {echoues} echoues")
    print("=" * 60)
