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
        PYTHON_SCRIPT="python3 Envelope2025/strategies/trix/multi_bitmart.py"
    elif [ "$ARGUMENT" == "trix_multi_bitmart_lite" ]; then
        PYTHON_SCRIPT="python3 Envelope2025/strategies/trix/multi_bitmart_lite.py"
    elif [ "$ARGUMENT" == "envelopes_multi_bitget" ]; then
        PYTHON_SCRIPT="python3 Envelope2025/strategies/envelopes/multi_bitget.py"
    else
        echo "Argument non reconnu. Aucun ajout ne sera effectué."
    fi

    # Si un script Python a été défini, procéder à l'ajout
    if [ -n "$PYTHON_SCRIPT" ]; then
        # Vérifier si la ligne existe déjà dans 1hcron.sh
        if grep -Fxq "$PYTHON_SCRIPT" Envelope2025/1hcron.sh; then
            echo "Le script $PYTHON_SCRIPT existe déjà dans 1hcron.sh"
        else
            # Ajouter la ligne au fichier 1hcron.sh
            echo "$PYTHON_SCRIPT" >> Envelope2025/1hcron.sh
            echo "Le script $PYTHON_SCRIPT a été ajouté à 1hcron.sh"
        fi
    fi
fi

echo "Mise à jour du serveur..."
sudo apt-get update

echo "Installation de pip..."
sudo apt install pip -y

echo "Installation des packages nécessaires..."
cd "Envelope2025"
sudo apt-get install python3-venv -y
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
git update-index --assume-unchanged secret.py

# Configuration des tâches cron
(crontab -l 2>/dev/null; echo "*/5 * * * * cd \"$(pwd)\" && /bin/bash ./BtcX1.sh >> \"$(pwd)/log/BtcX1.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0-59/5 * * * * cd \"$(pwd)\" && sleep 30 && /bin/bash ./BtcX2.sh >> \"$(pwd)/log/BtcX2.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * cd \"$(pwd)\" && /bin/bash ./BtcX5.sh >> \"$(pwd)/log/BtcX5.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * cd \"$(pwd)\" && sleep 30 && /bin/bash ./BtcX10.sh >> \"$(pwd)/log/BtcX10.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * cd \"$(pwd)\" && /bin/bash ./BtcX20.sh >> \"$(pwd)/log/BtcX20.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * cd \"$(pwd)\" && sleep 30 && /bin/bash ./BtcX30.sh >> \"$(pwd)/log/BtcX30.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * cd \"$(pwd)\" && /bin/bash ./AltX3High.sh >> \"$(pwd)/log/AltX3High.log\" 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * cd \"$(pwd)\" && sleep 30 && /bin/bash ./AltX3Traling.sh >> \"$(pwd)/log/AltX3Traling.log\" 2>&1") | crontab -

cd ..
echo "Installation terminée !"
