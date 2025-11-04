#  Smart City – Optimisation de la disponibilité des Vélib’ à Paris

**Auteurs :** Jacques LIN & Thomas COUTAREL  
**Projet :** Cloud AWS – Efrei M2 2024/2025  

---

##  Table des matières
1. [ Objectif](#-objectif)
2. [ Données utilisées](#️-données-utilisées)
3. [ Architecture AWS](#️-architecture-aws)
4. [ Pourquoi ces sources ?](#-pourquoi-ces-sources-)
5. [ Contenu du dépôt](#️-contenu-du-dépôt)
6. [ Accès aux ressources AWS](#-accès-aux-ressources-aws)
7. [ Problèmes rencontrés](#-problèmes-rencontrés)
8. [ Business Value](#-business-value)
9. [ Exécution locale](#-exécution-locale-optionnelle)
10. [ Auteurs](#-auteurs)

---

##  Objectif

L’objectif de ce projet est d’**optimiser la disponibilité des Vélib’ à Paris** en fonction :
- des **perturbations RATP (métros, lignes)**,
- et des **événements urbains** (concerts, expositions, etc.).  

En combinant plusieurs sources de données ouvertes et temps réel, notre plateforme vise à **anticiper les zones de tension** et à **rééquilibrer la flotte de vélos** selon le contexte de mobilité.

---

##  Données utilisées

| Source | Description | Type |
|--------|--------------|------|
| **API Vélib’** | Données temps réel des stations (nombre de vélos et bornes disponibles) | Streaming |
| **API RATP / IDFM (Navitia)** | Perturbations et incidents sur les lignes de métro | Streaming |
| **Open Data Mairie de Paris** | Événements culturels et manifestations | Batch |

à noter que pour les API Ile-de-france-mobilité il faut un compte et un token pour l'appeler 
---

##  Architecture AWS

<img width="1744" height="672" alt="cityflow_architecture_aws drawio(1)" src="https://github.com/user-attachments/assets/65e00842-da46-42b4-83e6-0e74d796d64b" />

   
Notre architecture repose sur plusieurs couches logiques :  

### 1. **Ingestion & Traitement**
- **AWS Lambda** pour le traitement et le nettoyage des données issues des APIs (Vélib’, RATP, événements).  
- **S3 (Bronze, Silver, Gold)** pour le stockage des données intermédiaires et fusionnées.  

### 2. **Stockage & Modélisation**
- **DynamoDB** comme DataMart final pour stocker les agrégations quotidiennes (fusion des 3 sources).  

### 3. **Exposition des données**
- **API Gateway** pour exposer les endpoints REST et permettre l’accès sécurisé aux données du DataMart.  
- **Dashboard interactif** (externe) permettant de visualiser les disponibilités et perturbations.  

---

##  Pourquoi ces sources ?

- Elles offrent une **vue complète de la mobilité urbaine**.
- En corrélant les incidents RATP et les événements avec la disponibilité Vélib’, on peut **détecter les zones à forte demande**.  
- Ces informations permettent de **prévoir les besoins de rééquilibrage** et d’**améliorer la disponibilité des stations**.

---

##  Contenu du dépôt

Ce dépôt contient :
- Le code des **fonctions AWS Lambda** :
- La ** collection de Postman ** avec les endpoints (optionnel).
- 

---

##  Accès aux ressources AWS

| Ressource | Accès |
|------------|--------|
| **API Gateway** | Endpoint REST public : [`https://<id>.execute-api.eu-west-3.amazonaws.com/prod/`](#) *(à remplacer par l’URL réelle)* |
| **S3 Bucket – Silver / Gold** | [`s3://proj-cloud-argent`](https://s3.console.aws.amazon.com/s3/buckets/proj-cloud-argent) |
| **S3 Bucket – Bronze** | [`s3://proj-cloud-brute`](https://s3.console.aws.amazon.com/s3/buckets/proj-cloud-brute) |
| **DynamoDB Table** | `datamart_fusion_csv` – stocke la fusion quotidienne des données |
| **Fonctions Lambda** | accessibles via la console AWS (nom : `velib_loader`, `datamarts`, `fusion_csv`) |

---

##  Problèmes rencontrés

| Composant | Problème | Solution |
|------------|-----------|-----------|
| **API RATP** | Filtrage des incidents actifs et pagination complexe | Filtrage sur `status=="active"` et gestion récursive des pages |
| **Silver Layer** | Fusion hétérogène des jeux de données | Nettoyage et harmonisation des schémas avant jointure |
| **DynamoDB** | Erreurs de clés primaires dupliquées | Génération de clés uniques combinant `date + station_id` |
| **API Gateway** | Liaison de clé API et permission Lambda | Création d’une ressource IAM dédiée et association manuelle |
| **AWS Lambda** | Erreurs d’import de `pandas`, `geopy`... | Packaging local avec `requirements.txt` et upload du `.zip` complet |

---

##  Business Value

- Données exposées via API Gateway → **exploitation sécurisée et standardisée**
- Dashboard interactif → **visualisation rapide des perturbations et de la disponibilité**
- Insights exploitables pour :
  - Anticiper les pics de demande
  - Rééquilibrer les stations
  - Améliorer la satisfaction usager

---

##  Lancer EC2 en local : 

          1 : pour ce connecter à son instance ec2 : 

ssh -i "clef_instanceec2.pem" ec2-user@ec2-35-181-63-154.eu-west-3.compute.amazonaws.com

          2 : Création du script Bash — Crée un script /home/ec2-user/upload_qdaparis_v2.sh qui télécharge le CSV “Que faire à Paris ?”, le vérifie et l’upload sur S3.

sudo tee /home/ec2-user/upload_qdaparis_v2.sh > /dev/null <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# ---------- paramètres ----------
BUCKET="proj-cloud-brute"
PREFIX="autre"                                    
FILENAME="que-faire-a-paris-v2.csv"              
LOCAL_PATH="/tmp/${FILENAME}"
S3_PATH="s3://${BUCKET}/${PREFIX}/${FILENAME}"
CSV_URL="https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/que-faire-a-paris-/exports/csv?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B"
LOG="/home/ec2-user/upload_qdaparis_v2.log"
# ---------------------------------

echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - START" | tee -a "$LOG"

curl -fSL --retry 3 --retry-delay 5 --connect-timeout 15 --max-time 300 "$CSV_URL" -o "$LOCAL_PATH"

if [ ! -s "$LOCAL_PATH" ]; then
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - ERROR: fichier téléchargé vide" | tee -a "$LOG"
  exit 2
fi

if head -n 1 "$LOCAL_PATH" | grep -qiE '<!DOCTYPE|<html'; then
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - ERROR: contenu reçu = HTML, pas CSV" | tee -a "$LOG"
  cp "$LOCAL_PATH" "${LOCAL_PATH}.html"   # sauvegarde pour debug
  exit 2
fi

HEADLINE=$(head -n 1 "$LOCAL_PATH" || echo "")
if ! echo "$HEADLINE" | grep -q ';'; then
  echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - WARNING: l'entête ne contient pas de ';' (vérifier le CSV)" | tee -a "$LOG"
fi

echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - Fichier téléchargé: ${LOCAL_PATH}" | tee -a "$LOG"
tail -n 3 "$LOCAL_PATH" | tee -a "$LOG"

/usr/bin/aws s3 cp "$LOCAL_PATH" "$S3_PATH" --only-show-errors
echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - Upload terminé: ${S3_PATH}" | tee -a "$LOG"

rm -f "$LOCAL_PATH"

echo "$(date -u +'%Y-%m-%dT%H:%M:%SZ') - FIN" | tee -a "$LOG"
EOF


sudo chmod +x /home/ec2-user/upload_qdaparis_v2.sh
sudo chown ec2-user:ec2-user /home/ec2-user/upload_qdaparis_v2.sh

sudo touch /home/ec2-user/upload_qdaparis_v2.log
sudo chown ec2-user:ec2-user /home/ec2-user/upload_qdaparis_v2.log
sudo chmod 644 /home/ec2-user/upload_qdaparis_v2.log

        3 : Exécution manuelle du script — Lance le script immédiatement et affiche les 50 dernières lignes du log pour vérifier le résultat.

/home/ec2-user/upload_qdaparis_v2.sh || echo "Erreur lors de l'exécution"
tail -n 50 /home/ec2-user/upload_qdaparis_v2.log

        4 : Création du cron job — Programme le script pour qu’il s’exécute automatiquement le 1er de chaque mois à 1h du matin.

crontab -l 2>/dev/null > /tmp/current_cron || true

(crontab -l 2>/dev/null | grep -v 'upload_qdaparis_v2.sh') | crontab -

( crontab -l 2>/dev/null; echo "0 1 1 * * /home/ec2-user/upload_qdaparis_v2.sh >> /home/ec2-user/upload_qdaparis_v2_cron.log 2>&1" ) | crontab -

crontab -l

        5 : Vérification du service cron — Vérifie que le démon crond (responsable des tâches planifiées) est bien actif.

sudo systemctl status crond --no-pager
 

