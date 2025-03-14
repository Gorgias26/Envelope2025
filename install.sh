#!/bin/bash

# Vérifier si un argument a été fourni
if [ -z "$1" ]; then
    echo "Aucun argument fourni. Aucun script ne sera ajouté à 1hcron.sh."
else
    # Récupérer l'argument
    ARGUMENT="$1"

    # Initialiser la variable pour le script Python
    PYTHON_SCRIPT=""

    # Déterminer le script Python en fonction de l'argument
    if [ "$ARGUMENT" == "trix_multi_bitmart" ]; then
        PYTHON_SCRIPT="python3 Live-Tools-V2/strategies/trix/multi_bitmart.py"
    elif [ "$ARGUMENT" == "trix_multi_bitmart_lite" ]; then
        PYTHON_SCRIPT="python3 Live-Tools-V2/strategies/trix/multi_bitmart_lite.py"
    elif [ "$ARGUMENT" == "envelopes_multi_bitget" ]; then
        PYTHON_SCRIPT="python3 Live-Tools-V2/strategies/envelopes/multi_bitget.py"
    else
        echo "Argument non reconnu. Aucun ajout ne sera effectué."
    fi

    # Si un script Python a été défini, procéder à l'ajout
    if [ -n "$PYTHON_SCRIPT" ]; then
        # Vérifier si la ligne existe déjà dans 1hcron.sh
        if grep -Fxq "$PYTHON_SCRIPT" Live-Tools-V2/1hcron.sh; then
            echo "Le script $PYTHON_SCRIPT existe déjà dans 1hcron.sh"
        else
            # Ajouter la ligne au fichier 1hcron.sh
            echo "$PYTHON_SCRIPT" >> Live-Tools-V2/1hcron.sh
            echo "Le script $PYTHON_SCRIPT a été ajouté à 1hcron.sh"
        fi
    fi
fi

echo "Mise à jour du serveur..."
sudo apt-get update

echo "Installation de pip..."
sudo apt install pip -y

# Obtenir le chemin absolu du dossier de travail
WORKDIR="$(pwd)/Live-Tools-V2-main 2025"

# Créer le dossier log
mkdir -p "$WORKDIR/log"

echo "Installation des packages nécessaires..."
cd "$WORKDIR"
sudo apt-get install python3-venv -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git update-index --assume-unchanged secret.py

# Configuration des permissions des scripts
echo "Configuration des permissions..."
chmod +x *.sh

# Configuration des tâches cron avec le bon chemin
echo "Configuration du crontab..."
(crontab -l 2>/dev/null; echo "*/5 * * * * cd \"$WORKDIR\" && /bin/bash \"$WORKDIR/BtcX1.sh\" >> \"$WORKDIR/log/BtcX1.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0-59/5 * * * * cd \"$WORKDIR\" && sleep 30 && /bin/bash \"$WORKDIR/BtcX2.sh\" >> \"$WORKDIR/log/BtcX2.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * cd \"$WORKDIR\" && /bin/bash \"$WORKDIR/BtcX5.sh\" >> \"$WORKDIR/log/BtcX5.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * cd \"$WORKDIR\" && sleep 30 && /bin/bash \"$WORKDIR/BtcX10.sh\" >> \"$WORKDIR/log/BtcX10.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * cd \"$WORKDIR\" && /bin/bash \"$WORKDIR/BtcX20.sh\" >> \"$WORKDIR/log/BtcX20.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * cd \"$WORKDIR\" && sleep 30 && /bin/bash \"$WORKDIR/BtcX30.sh\" >> \"$WORKDIR/log/BtcX30.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * cd \"$WORKDIR\" && /bin/bash \"$WORKDIR/AltX3High.sh\" >> \"$WORKDIR/log/AltX3High.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * cd \"$WORKDIR\" && sleep 30 && /bin/bash \"$WORKDIR/AltX3Traling.sh\" >> \"$WORKDIR/log/AltX3Traling.log\" 2>&1") | crontab -

# Vérifications finales
echo "Vérification du crontab..."
crontab -l

echo "Vérification des permissions des scripts..."
ls -l *.sh

echo "Installation terminée ! N'oubliez pas de configurer votre fichier secret.py"
echo "Chemin de travail : $WORKDIR"
