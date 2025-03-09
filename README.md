# TikTok Bot 

Ce projet est un bot automatisé permettant de générer des videos musicales et de les publier sur TikTok. Il intègre diverses fonctionnalités de traitement vidéo et audio pour améliorer l'expérience utilisateur.

## 🚀 Fonctionnalités

- **Téléchargement automatique** des vidéos depuis YouTube et TikTok.
- **Détection des battements** dans la musique pour ajouter des effets de flash.
- **Ajout de titres et de transitions** pour améliorer la qualité des vidéos.
- **Automatisation complète** du processus d'upload sur TikTok avec Selenium.
- **Gestion des vidéos et des sons** pour éviter les doublons et optimiser la viralité.

## 📦 Dépendances

Avant de lancer le script, assure-toi d'avoir installé les bibliothèques suivantes :

```bash
pip install imageio numpy moviepy tiktokapipy asyncio opencv-python librosa selenium requests pytube pandas undetected-chromedriver chromedriver-autoinstaller
```

## 🛠 Configuration

Settings are stored in various JSON files and Python scripts. You can modify:

- Params_bot.py to adjust bot preferences.

- Used_videos_3*.py to manage used videos.

- audios_params.json to configure music settings.

## 📝 License

This project is licensed under the MIT License. Feel free to use and modify it.

## 🤝 Contribute

Contributions are welcome! Open an issue or submit a pull request if you have ideas or improvements.

## Disclaimer 

This bot is not affiliated with TikTok. By using this tool, you agree to follow TikTok’s Terms of Service and understand that automated actions may result in account suspension. Use at your own risk, and ensure your actions comply with TikTok's Community Guidelines. The creators are not responsible for any consequences, including account bans or data loss. Use ethically and responsibly.
