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

# Création des dossiers et fichiers log
mkdir -p log
touch log/BtcX1.log log/BtcX2.log log/BtcX5.log log/BtcX10.log log/BtcX20.log log/BtcX30.log log/AltX3High.log log/AltX3Traling.log

# Suppression des anciennes entrées cron
crontab -r

# Ajout des nouvelles entrées cron
(crontab -l 2>/dev/null; echo "*/5 * * * * bash /home/ubuntu/Envelope2025/BtcX1.sh >> /home/ubuntu/Envelope2025/log/BtcX1.log") | crontab -
(crontab -l 2>/dev/null; echo "0-59/5 * * * * sleep 30 && bash /home/ubuntu/Envelope2025/BtcX2.sh >> /home/ubuntu/Envelope2025/log/BtcX2.log") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * bash /home/ubuntu/Envelope2025/BtcX5.sh >> /home/ubuntu/Envelope2025/log/BtcX5.log") | crontab -
(crontab -l 2>/dev/null; echo "1-59/5 * * * * sleep 30 && bash /home/ubuntu/Envelope2025/BtcX10.sh >> /home/ubuntu/Envelope2025/log/BtcX10.log") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * bash /home/ubuntu/Envelope2025/BtcX20.sh >> /home/ubuntu/Envelope2025/log/BtcX20.log") | crontab -
(crontab -l 2>/dev/null; echo "2-59/5 * * * * sleep 30 && bash /home/ubuntu/Envelope2025/BtcX30.sh >> /home/ubuntu/Envelope2025/log/BtcX30.log") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * bash /home/ubuntu/Envelope2025/AltX3High.sh >> /home/ubuntu/Envelope2025/log/AltX3High.log") | crontab -
(crontab -l 2>/dev/null; echo "3-59/5 * * * * sleep 30 && bash /home/ubuntu/Envelope2025/AltX3Traling.sh >> /home/ubuntu/Envelope2025/log/AltX3Traling.log") | crontab -

cd ..

# Attribution des permissions d'exécution
chmod +x /home/ubuntu/Envelope2025/BtcX1.sh
chmod +x /home/ubuntu/Envelope2025/BtcX2.sh
chmod +x /home/ubuntu/Envelope2025/BtcX5.sh
chmod +x /home/ubuntu/Envelope2025/BtcX10.sh
chmod +x /home/ubuntu/Envelope2025/BtcX20.sh
chmod +x /home/ubuntu/Envelope2025/BtcX30.sh
chmod +x /home/ubuntu/Envelope2025/AltX3High.sh
chmod +x /home/ubuntu/Envelope2025/AltX3Traling.sh

echo "Installation terminée !"
