# 🧨 Creeper — Bot Discord complet pour serveur Minecraft 🎮

Bienvenue dans **Creeper**, un bot Discord 100 % en **Python** 🇫🇷 conçu pour automatiser, personnaliser et améliorer un serveur Discord dédié à **Minecraft**.  
Ce projet est pensé pour une classe **BTS SIO** qui veut un serveur organisé, fonctionnel et fun pour jouer ensemble 👨‍💻🧱

---

## 🚀 Fonctionnalités principales

✅ **Commande `/setup`** : en une commande, Creeper configure tout votre serveur Discord avec un thème Minecraft :  
- Création automatique des **catégories et salons** : général, annonces, screenshots, aide, projets, etc.  
- Ajout de **salons vocaux** pour discuter et jouer  
- Création d’un **salon musical** 🎶  
- Message d’accueil automatique pour les nouveaux membres  
- Ajout des **rôles de base** : `👑 Admin`, `🔧 Modérateur`, `🧱 Joueur`, `🤖 Bot`  

🎵 **Système musical YouTube intégré** :  
- `/play <lien ou recherche>` → joue de la musique depuis YouTube  
- `/skip`, `/stop`, `/pause`, `/resume` → contrôle total de la file d’attente  
- Support des **liens YouTube, playlists et recherches**  
- Utilise `yt_dlp` + `FFmpeg` pour la lecture audio  

📩 **Fonctions supplémentaires** :  
- Message d’accueil personnalisé  
- Commande `/help` pour voir toutes les commandes disponibles  
- Salon `#📚-logs` pour suivre les actions importantes du bot  

---

## 📁 Structure du projet

```bash
creeper-discord-bot/
├── cogs/
│   ├── setup.py       # Commande /setup et création automatique du serveur
│   ├── music.py       # Gestion complète du système musical
│   ├── welcome.py     # Message d’accueil automatique
│   ├── roles.py       # Gestion des rôles
│   └── help.py        # Commande /help
├── utils/
│   ├── checks.py      # Fonctions de vérification de permissions
│   ├── config.py      # Variables globales
│   └── embeds.py      # Fonctions pour messages stylés
├── main.py            # Point d’entrée principal
├── requirements.txt   # Liste des dépendances
└── README.md          # Ce fichier 📜
```

---

## ⚙️ Installation & lancement
1. Cloner le projet
```bash
git clone https://github.com/fzazdbl/creeper-discord-bot.git
cd creeper-discord-bot
```

---

## 2. Créer un environnement virtuel (optionnel)
```bash
python -m venv venv
source venv/bin/activate     # macOS / Linux
venv\Scripts\activate        # Windows
```

---

## 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

---
## 4. Installer FFmpeg
**Windows :** télécharge-le depuis https://ffmpeg.org et ajoute le dossier bin à ta variable d’environnement PATH.
**Linux/macOS :**
```bash
sudo apt install ffmpeg
```

---
## 5. Créer un fichier .env
Dans le dossier principal, crée un fichier nommé .env et ajoute ton token Discord :
```bash
DISCORD_TOKEN=ton_token_ici
```
---
## 6. Lancer le bot
```bash
python main.py
```



