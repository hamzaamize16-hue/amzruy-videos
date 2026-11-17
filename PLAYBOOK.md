# Amzruy n Umaḍal: production quotidienne (PLAYBOOK)

Chaîne YouTube d'histoire en **darija** (Maroc + monde), format **Shorts verticaux**.
Objectif : **maximum de vues et d'interactions**, avec des faits vrais et une vidéo de haute qualité.
Publication : **chaque jour à 19:00 Europe/Paris** via Metricool, réseau YouTube, type `short`.

Ce dépôt contient tout le nécessaire :
- `engine/render_ep01.py` : moteur de rendu (fond nuit + graticule, poussière dorée, grain, sous-titres darija, filigrane, barre de progression, outro de marque, carte animée, parchemin, compteur, etc.). Épisode 1 = modèle à copier.
- `engine/audio_ep01.py` : musique originale (hijaz : oud, drone, bendir) + effets + voix découpée par scène + ducking.
- `engine/brand.py` + `brand/` : logo astrolabe-globe et déclinaisons.
- `episodes/EPxx/` : `final.mp4`, `script.md`, `metadata.json`, `voice_saad.mp3`.
- `episodes.json` : journal de tous les épisodes (pour ne jamais répéter un sujet, un hook ou un style visuel).

---

## 0. Démarrage (5 min)
1. Lire ce PLAYBOOK et `episodes.json` (sujets, hooks et styles déjà utilisés).
2. Prérequis à vérifier :
   - Metricool : `getBrandSettings` → la marque **7721494** doit avoir `networksData.youtubeData` = **UCj7QL0MrpADd1XRrxt6aIIQ** (chaîne « Amzruy N'umadal », @Amzruy_Numadal). Si l'identifiant de chaîne est différent (par exemple l'ancienne chaîne @tillasquotes, UC20jdUQGBQwRJsB3LdTnSMQ) : **ne rien publier** et prévenir l'utilisateur.
   - Ordinateur de l'utilisateur joignable (navigateur intégré + dossier Téléchargements) pour la voix ElevenLabs.
3. Si un prérequis manque : produire quand même la vidéo jusqu'où c'est possible, **ne rien publier**, prévenir l'utilisateur (PushNotification / SendUserMessage) avec ce qui manque.

## 1. Veille et choix du sujet (15 min)
Faire au moins 5 recherches web, dont :
- « on this day » / « حدث في مثل هذا اليوم » pour la date de publication (anniversaires historiques, Maroc et monde) ;
- actualité du jour au Maroc et dans le monde qui peut avoir un angle historique (film, sport, fête nationale, découverte archéologique, débat viral) ;
- sujets d'histoire qui font le buzz en ce moment (Shorts/TikTok/Reels histoire, tendances arabes et francophones) ;
- si l'outil vidIQ a des crédits : `vidiq_trending_videos` (videoFormat short, titleQuery « تاريخ » / « history », videoTitleLanguage ar puis all) et `vidiq_outliers`.

Noter chaque sujet candidat de 1 à 5 sur : **curiosité / effet « wow »**, **lien avec l'actualité ou une date**, **fierté ou émotion pour un public marocain et maghrébin**, **potentiel visuel**, **faits vérifiables**. Choisir le meilleur total. Ne pas reprendre un sujet de `episodes.json`.

Banque d'idées (à vérifier avant usage) : Fête de l'Indépendance (18 novembre) ; Ibn Battuta et ses ~120 000 km ; Fatima al-Fihri et al-Qarawiyyin (859) ; la carte du monde d'al-Idrissi ; Estevanico (Mustafa Azemmouri), premier Africain à explorer l'Amérique du Nord ; la république corsaire du Bouregreg (Salé) ; la bataille des Trois Rois (1578) ; Tariq ibn Ziyad et le nom « Gibraltar » ; Volubilis ; Moulay Ismaïl et Meknès ; la Koutoubia et la Giralda de Séville, minarets jumeaux ; les grandes inventions et énigmes de l'histoire mondiale reliées au Maroc.

Sujets à éviter : polémiques politiques actuelles, religion présentée de façon clivante, violence graphique, tout ce qu'on ne peut pas sourcer.

## 2. Vérification des faits (10 min)
- Chaque date, chiffre et nom doit être confirmé par **au moins 2 sources fiables** (sites officiels, encyclopédies, universités, grands médias). Les garder pour `metadata.json` → `sources`.
- En cas de doute, retirer l'affirmation ou la nuancer. Ne jamais inventer.

## 3. Script darija (10 min)
- **Durée cible : 40 à 55 s** (environ 100 à 140 mots). Plus court = meilleur taux de rétention.
- **Hook (≤ 3 s)** : voix + texte + visuel en même temps. Varier le type à chaque épisode : question (« واش عرفتي… ؟ »), chiffre choc, contradiction (« الكل كيظن… ولكن… »), mystère, défi (« 99% ما عارفينش… »).
- Une surprise au milieu (« والمفاجأة؟… »), une révélation finale, puis CTA : une **question pour faire commenter** + « تبعنا ».
- Darija naturelle et simple ; écrire les années en toutes lettres pour la voix (« ألف وسبعمية… ») mais en chiffres dans les sous-titres.
- Un paragraphe = une scène (8 à 10 scènes, changement visuel toutes les 2 à 3 s).
- Sauver dans `episodes/EPxx/script.md` (texte voix + sous-titres par scène).

## 4. Voix (ElevenLabs, navigateur intégré de l'ordinateur de l'utilisateur)
1. `Claude_Browser__preview_start` → `https://elevenlabs.io/app/speech-synthesis/text-to-speech` (session déjà connectée ; ne jamais saisir de mot de passe ; si déconnecté : stop et prévenir).
2. Voix : **« Saad - Moroccan Mystery Storyteller »** (si autre voix affichée : clic sur la puce de voix → recherche « Moroccan » → Saad).
3. Texte : `find("textbox")` puis `form_input` avec le script (paragraphes séparés par une ligne vide). Taper avec `type` ne marche pas pour l'arabe.
4. Cliquer « Générer un discours », attendre ~15 s, cliquer l'icône de téléchargement de **Génération 1**.
5. Le fichier arrive dans `C:\Users\hamza\Downloads` avec un nom `xxxxxxxx-....tmp` (≈ 0,9 Mo pour 60 s). `device_list_dir` → prendre le plus récent → `device_stage_files` → copier en `voice.mp3`.
6. Vérifier les crédits restants (bas de page). Plan Starter : 30 000 crédits/mois.

## 5. Rendu vidéo (30 à 45 min)
- Copier `engine/render_ep01.py` → `episodes/EPxx/render.py` et `engine/audio_ep01.py` → `episodes/EPxx/audio.py`.
- Garder l'identité : fond, graticule, poussière, grain, vignettage, sous-titres (pastille, 62 px, contour), filigrane en haut à gauche, barre de progression, **outro de marque** (emblème + nom + « تابع + »). Couleurs : nuit `#0B1630`, or `#E9BD5C`, rouge `#C1272D`, vert `#0E6E50`, parchemin `#ECDCB6`.
- **Créer des scènes nouvelles adaptées au sujet** (personnages en silhouette, cartes, objets, monuments dessinés, frises, chiffres animés…). Ne jamais réutiliser la même suite de scènes d'un épisode à l'autre : la politique YouTube sur le « contenu inauthentique / répétitif » démonétise les chaînes dont les vidéos semblent faites au même gabarit.
- Pas de photos de personnes réelles, pas de personnages ni logos protégés.
- Voix : repérer les pauses (énergie RMS par 0,1 s), découper une phrase par scène, ajuster la durée des scènes à la voix (+0,3 s).
- Musique : changer à chaque épisode le motif, le tempo ou le mode (hijaz, nahawand, bayati…), ducking sous la voix.
- **Contrôle qualité obligatoire** : regarder 6 à 8 images clés (texte lisible, rien de coupé, arabe bien formé, pas de chevauchement), vérifier la durée, l'audio et le volume (-14 LUFS).
- Encodage final : 1080×1920, 30 i/s, H.264 `-preset slow -crf 25 -maxrate 3500k -bufsize 7000k`, AAC 192k, `-movflags +faststart` → **< 40 Mo**.

## 6. Publication
1. `episodes/EPxx/metadata.json` : titre (≤ 100 car., darija + emoji + `#shorts`), description (résumé, question pour les commentaires, CTA, sources, 6 à 8 hashtags), tags (arabe + français + anglais), `category: EDUCATION`.
2. Commit + push de `episodes/EPxx/` sur `main` du dépôt **hamzaamize16-hue/amzruy-videos** (public). URL publique : `https://raw.githubusercontent.com/hamzaamize16-hue/amzruy-videos/main/episodes/EPxx/final.mp4`.
3. Metricool `createScheduledPost` : `blogId` 7721494 (après vérification de la chaîne UCj7QL0MrpADd1XRrxt6aIIQ), `date` = aujourd'hui 19:00 Europe/Paris, `info` :
   `{"autoPublish":true,"draft":false,"text":"<description>","media":["<url raw>"],"providers":[{"network":"youtube"}],"publicationDate":{"dateTime":"YYYY-MM-DDT19:00:00","timezone":"Europe/Paris"},"youtubeData":{"title":"<titre>","type":"short","privacy":"public","tags":[...],"category":"EDUCATION","madeForKids":false,"isAiGeneratedContent":false},"descendants":[],"firstCommentText":"<question pour lancer les commentaires>","hasNotReadNotes":false,"mediaAltText":[],"shortener":false,"smartLinkData":{"ids":[]}}`
4. Mettre à jour `episodes.json` (sujet, angle, type de hook, style visuel, lien Metricool) et pousser.
5. Ménage : supprimer du dépôt les `final.mp4` des épisodes publiés depuis plus de 3 jours (le dépôt doit rester léger).

## 7. Compte rendu
Envoyer à l'utilisateur un message court : sujet, titre, heure de publication, lien Metricool, sources, et tout problème rencontré.
