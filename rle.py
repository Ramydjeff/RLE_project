"""
rle.py -- Le COEUR du projet : encodeur et decodeur RLE.

IMPORTANT : ce fichier n'importe NI cv2 NI numpy.
On travaille sur des simples listes de nombres (0 ou 255).
=> On peut le tester tout seul, sans ouvrir aucune fenetre.

RAPPEL DU CODAGE DEMANDE PAR LE PROF
------------------------------------
Chaque "bloc" commence par un MOT DE 2 OCTETS (= un entier sur 16 bits).
Le bit le plus a gauche (bit 15) dit de quel type de bloc il s'agit :

  bit15 = 1  ->  BLOC REPETITION
                 Les 15 autres bits = combien de fois le pixel se repete.
                 Puis on ecrit 1 octet : la couleur repetee.
                 Exemple : 80 04 FF  =  "blanc, 4 fois"
                 Cout : TOUJOURS 3 octets, peu importe la longueur.

  bit15 = 0  ->  BLOC LITTERAL
                 Les 15 autres bits = combien de pixels suivent.
                 Puis on recopie ces pixels tels quels.
                 Exemple : 00 04 00 FF 00 00  =  "4 pixels bruts : 00 FF 00 00"
                 Cout : 2 octets + la taille de la suite.

On utilise un bloc REPETITION seulement a partir de 3 pixels identiques,
car en dessous ce n'est pas rentable (3 octets pour coder 2 pixels = perte).
"""

# ---------------------------------------------------------------------------
# CONSTANTES
# ---------------------------------------------------------------------------

NOIR = 0      # 0x00
BLANC = 255   # 0xFF

# Le compteur tient sur 15 bits -> valeur maximale = 2^15 - 1 = 32767.
# Si un run est plus long, on le decoupe en plusieurs blocs.
MAX_RUN = 32767          # 0x7FFF  (binaire : 0111 1111 1111 1111)

# Le "drapeau" du bit 15. Faire "mot = BIT_REPETITION | nb" met ce bit a 1.
BIT_REPETITION = 0x8000  # binaire : 1000 0000 0000 0000


# ---------------------------------------------------------------------------
# PETITS OUTILS SUR LE MOT DE 16 BITS
# ---------------------------------------------------------------------------

def construire_mot(est_repetition, nombre):
    """
    Fabrique le mot de 2 octets.

    est_repetition : True  -> bit15 = 1 (bloc repetition)
                     False -> bit15 = 0 (bloc litteral)
    nombre         : la valeur a coder sur les 15 bits du bas (1 .. 32767)

    Exemple : construire_mot(True, 4) -> 0x8004
    """
    if not (1 <= nombre <= MAX_RUN):
        raise ValueError(f"nombre={nombre} hors limites (1..{MAX_RUN})")

    if est_repetition:
        return BIT_REPETITION | nombre   # on allume le bit 15
    else:
        return nombre                    # bit 15 reste a 0


def lire_mot(mot):
    """
    Opération inverse : on casse le mot de 16 bits en deux informations.

    Retourne un couple (est_repetition, nombre).

    mot >> 15     : on decale de 15 crans a droite -> il ne reste que le bit 15
    mot & 0x7FFF  : on garde seulement les 15 bits du bas (on masque le bit 15)
    """
    est_repetition = (mot >> 15) == 1
    nombre = mot & MAX_RUN
    return est_repetition, nombre


def mot_en_octets(mot):
    """
    Coupe l'entier 16 bits en 2 octets, en BIG-ENDIAN
    (= l'octet de poids fort en premier, comme on lit un nombre).

    Exemple : 0x8004 -> [0x80, 0x04]
    """
    octet_fort = (mot >> 8) & 0xFF   # les 8 bits du haut
    octet_faible = mot & 0xFF        # les 8 bits du bas
    return [octet_fort, octet_faible]


def octets_en_mot(octet_fort, octet_faible):
    """
    Operation inverse : recolle 2 octets en un entier 16 bits.

    Exemple : (0x80, 0x04) -> 0x8004
    """
    return (octet_fort << 8) | octet_faible


# ---------------------------------------------------------------------------
# FONCTION AUXILIAIRE : compter une repetition
# ---------------------------------------------------------------------------

def longueur_repetition(pixels, debut):
    """
    Compte combien de fois le pixel pixels[debut] se repete d'affilee.

    Exemple : pixels = [255, 255, 255, 0, ...], debut = 0  ->  retourne 3
    """
    valeur = pixels[debut]
    i = debut
    while i < len(pixels) and pixels[i] == valeur:
        i += 1
    return i - debut


# ---------------------------------------------------------------------------
# ENCODAGE
# ---------------------------------------------------------------------------

def encode(pixels, trace=False):
    """
    Compresse une liste 1D de pixels (0 ou 255) en une suite d'octets.

    pixels : liste/sequence de 0 et 255 (l'image aplatie)
    trace  : si True, affiche le tableau detaille des etapes (exige par le mail)

    Retourne : un objet bytes (les blocs RLE, SANS en-tete fichier)
    """
    sortie = bytearray()   # on accumule les octets produits ici
    lignes_trace = []      # pour l'affichage detaille
    i = 0                  # position de lecture dans pixels
    n = len(pixels)

    while i < n:
        # --- Combien de pixels identiques a partir de la position i ? ---
        r = longueur_repetition(pixels, i)

        if r >= 3:
            # =============== CAS 1 : BLOC REPETITION ===============
            couleur = pixels[i]
            restant = r

            # Si r > 32767, on ne peut pas le coder d'un coup :
            # on emet plusieurs blocs repetition a la suite.
            while restant > 0:
                paquet = min(restant, MAX_RUN)

                mot = construire_mot(True, paquet)
                octets = mot_en_octets(mot) + [couleur]
                sortie.extend(octets)

                lignes_trace.append({
                    "pixels_lus": f"{couleur:02X} x{paquet}",
                    "type": "REPETITION",
                    "mot": mot,
                    "octets": octets,
                })
                restant -= paquet

            i += r   # on saute toute la repetition

        else:
            # =============== CAS 2 : BLOC LITTERAL ===============
            # On avance tant qu'on ne rencontre PAS une repetition de 3+.
            debut = i

            while i < n:
                # Garde-fou : un bloc litteral ne peut pas depasser 32767
                if (i - debut) >= MAX_RUN:
                    break
                # Si une repetition de 3+ commence ici, on arrete le litteral
                # JUSTE AVANT (c'est le "piege n°1" du guide).
                if longueur_repetition(pixels, i) >= 3:
                    break
                # Sinon ce pixel (ou ces 2 pixels) rejoint le litteral.
                i += 1

            taille = i - debut
            morceau = list(pixels[debut:i])

            mot = construire_mot(False, taille)
            octets = mot_en_octets(mot) + morceau
            sortie.extend(octets)

            lignes_trace.append({
                "pixels_lus": " ".join(f"{p:02X}" for p in morceau),
                "type": "LITTERAL",
                "mot": mot,
                "octets": octets,
            })

    if trace:
        afficher_trace(lignes_trace, n, len(sortie), "ENCODAGE")

    return bytes(sortie)


# ---------------------------------------------------------------------------
# DECODAGE
# ---------------------------------------------------------------------------

def decode(donnees, nb_pixels_attendu=None, trace=False):
    """
    Decompresse une suite d'octets RLE et retrouve la liste de pixels.

    donnees           : bytes produits par encode()
    nb_pixels_attendu : largeur*hauteur, pour verifier qu'on n'a rien perdu
    trace             : si True, affiche le tableau detaille

    Retourne : une liste de 0 et 255
    """
    pixels = []
    lignes_trace = []
    i = 0
    taille_donnees = len(donnees)

    while i < taille_donnees:
        # --- 1) Lire le mot de 2 octets ---
        if i + 2 > taille_donnees:
            raise ValueError(f"Fichier corrompu : mot incomplet a l'offset {i}")

        mot = octets_en_mot(donnees[i], donnees[i + 1])
        octets_du_bloc = [donnees[i], donnees[i + 1]]
        i += 2

        # --- 2) Analyser le mot ---
        est_repetition, nombre = lire_mot(mot)

        if nombre == 0:
            raise ValueError(f"Fichier corrompu : bloc de taille 0 a l'offset {i-2}")

        if est_repetition:
            # =============== BLOC REPETITION ===============
            if i >= taille_donnees:
                raise ValueError(f"Fichier corrompu : couleur manquante a l'offset {i}")

            couleur = donnees[i]
            octets_du_bloc.append(couleur)
            i += 1

            pixels.extend([couleur] * nombre)   # on "deplie" la repetition

            lignes_trace.append({
                "pixels_lus": f"{couleur:02X} x{nombre}",
                "type": "REPETITION",
                "mot": mot,
                "octets": octets_du_bloc,
            })

        else:
            # =============== BLOC LITTERAL ===============
            if i + nombre > taille_donnees:
                raise ValueError(
                    f"Fichier corrompu : {nombre} octets attendus a l'offset {i}"
                )

            morceau = list(donnees[i:i + nombre])
            octets_du_bloc.extend(morceau)
            i += nombre

            pixels.extend(morceau)   # on recopie tel quel

            lignes_trace.append({
                "pixels_lus": " ".join(f"{p:02X}" for p in morceau),
                "type": "LITTERAL",
                "mot": mot,
                "octets": octets_du_bloc,
            })

    # --- 3) Verification de coherence ---
    if nb_pixels_attendu is not None and len(pixels) != nb_pixels_attendu:
        raise ValueError(
            f"Incoherence : {len(pixels)} pixels decodes, "
            f"{nb_pixels_attendu} attendus."
        )

    if trace:
        afficher_trace(lignes_trace, len(pixels), taille_donnees, "DECODAGE")

    return pixels


# ---------------------------------------------------------------------------
# AFFICHAGE DE LA TRACE DETAILLEE (exige par le mail du prof)
# ---------------------------------------------------------------------------

def afficher_trace(lignes, nb_pixels, nb_octets, titre, max_lignes=40):
    """
    Affiche le tableau :
      # | pixels lus | type | mot (bin) | hex | octets emis
    """
    print()
    print(f"===== TRACE DETAILLEE : {titre} =====")
    entete = (
        f"{'#':>4} | {'pixels lus':<22} | {'type':<10} | "
        f"{'mot (binaire)':<16} | {'hex':<4} | octets"
    )
    separateur = "-" * len(entete)
    print(entete)
    print(separateur)

    for numero, ligne in enumerate(lignes, start=1):
        # On tronque l'apercu des pixels si c'est trop long, pour rester lisible
        apercu = ligne["pixels_lus"]
        if len(apercu) > 22:
            apercu = apercu[:19] + "..."

        octets_txt = " ".join(f"{o:02X}" for o in ligne["octets"][:6])
        if len(ligne["octets"]) > 6:
            octets_txt += " ..."

        print(
            f"{numero:>4} | {apercu:<22} | {ligne['type']:<10} | "
            f"{ligne['mot']:016b} | {ligne['mot']:04X} | {octets_txt}"
        )

        if numero >= max_lignes:
            print(f"     ... ({len(lignes) - max_lignes} blocs supplementaires masques)")
            break

    print(separateur)
    print(f"Pixels : {nb_pixels}  |  Octets RLE : {nb_octets}  |  Blocs : {len(lignes)}")
    print()


# ---------------------------------------------------------------------------
# AUTO-TEST RAPIDE : lancer "python rle.py" pour verifier le coeur
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # L'exemple a la main du guide (section 3)
    exemple = [255, 255, 255, 255, 0, 255, 0, 0, 255, 255, 255]
    attendu = bytes([0x80, 0x04, 0xFF,
                     0x00, 0x04, 0x00, 0xFF, 0x00, 0x00,
                     0x80, 0x03, 0xFF])

    resultat = encode(exemple, trace=True)

    print("Resultat obtenu :", " ".join(f"{b:02X}" for b in resultat))
    print("Resultat attendu:", " ".join(f"{b:02X}" for b in attendu))
    print("Encodage conforme au guide :", resultat == attendu)

    retour = decode(resultat, nb_pixels_attendu=len(exemple), trace=True)
    print("Decodage sans perte :", retour == exemple)
