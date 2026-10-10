# Codec RLE pour images binaires

Projet n°1 — Communication Multimédia — Master Informatique Visuelle, USTHB 2026/2027

Compression/décompression d'images binaires (0 = noir, 255 = blanc) par la
technique RLE, avec affichage détaillé de chaque étape.

## Lancer le projet

```powershell
.\.venv\Scripts\activate      # activer l'environnement
python main.py                # menu principal
python tests.py               # tests automatiques (34 tests)
python rle.py                 # auto-test du coeur uniquement
```

## Les fichiers

| Fichier | Rôle |
|---|---|
| `rle.py` | **Le cœur** : `encode()` / `decode()` + trace. Aucun import OpenCV. |
| `fileio.py` | `save_rle()` / `load_rle()` : en-tête 4 octets + blocs. |
| `draw.py` | Fenêtre OpenCV, dessin souris, affichage, mode texte de secours. |
| `main.py` | Menu CLI qui orchestre tout. |
| `tests.py` | Tests automatiques (cas limites du guide). |
| `sorties/` | Fichiers `.png` et `.rle` générés. |

## Le format de codage

Chaque bloc commence par un **mot de 2 octets** (big-endian) :

```
bit 15 = 1  ->  REPETITION : 15 bits = nb de répétitions, puis 1 octet couleur
                Exemple : 80 04 FF  =  blanc répété 4 fois        (3 octets)

bit 15 = 0  ->  LITTERAL   : 15 bits = taille, puis les pixels bruts
                Exemple : 00 04 00 FF 00 00  =  4 pixels bruts    (2+n octets)
```

Un bloc répétition n'est utilisé qu'à partir de **3 pixels identiques** : en
dessous, les 3 octets coûteraient plus cher que les pixels eux-mêmes.

Maximum codable sur 15 bits : **32767**. Au-delà, le run est découpé en
plusieurs blocs.

## Le fichier `.rle`

```
+----------+----------+------------------------+
| Largeur  | Hauteur  |  Blocs RLE             |
| 2 octets | 2 octets |  taille variable       |
+----------+----------+------------------------+
```

L'en-tête est indispensable : sans les dimensions, le décodeur obtient une
suite de pixels 1D qu'il ne peut pas remettre en 2D.

## Commandes de la fenêtre de dessin

| Touche / souris | Effet |
|---|---|
| clic gauche | peindre en noir |
| clic droit | gommer (blanc) |
| `s` | valider le dessin |
| `r` | tout effacer |
| `i` | inverser les couleurs |
| `q` | annuler |

Si la fenêtre ne s'ouvre pas, l'option `7` du menu bascule en mode texte
(`#` = noir, `.` = blanc).

## Résultats observés

Formule du taux : $\text{Taux} = \left(1 - \frac{\text{Taille compressée}}{\text{Taille originale}}\right) \times 100$

- **Positif (`+`)** : gain de place (compression efficace).
- **Négatif (`−`)** : le fichier a grossi (expansion, cas d'une alternance fréquente de pixels).

| Image | Original | Compressé | Taux |
|---|---|---|---|
| Carré noir 32×32 | 1024 o | 103 o | **+89,94 %** |
| Dessin 6×8 (cœur) | 48 o | 39 o | **+18,75 %** |
| Exemple du guide (11 px) | 11 o | 12 o | **−9,09 %** |
| Damier 16×16 | 256 o | 262 o | **−2,34 %** |

Le taux dépend entièrement du contenu : le RLE **agrandit** les images
bruitées ou trop courtes, car chaque bloc impose son mot de contrôle de 2 octets.
