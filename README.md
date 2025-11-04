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

