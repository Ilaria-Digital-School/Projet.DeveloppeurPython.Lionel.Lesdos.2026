# Systeme de Notifications

Ce document decrit le systeme de notifications de l'application Budget App.

## Architecture

Le systeme de notifications est compose des elements suivants :

1. **Modeles de donnees** :
   - `Notification` : Stocke les notifications des utilisateurs
   - `NotificationPreference` : Stocke les preferences de notification par type

2. **Service** :
   - `NotificationService` : Gere la creation, l'envoi et la lecture des notifications
   - Envoi d'emails via Flask-Mail (synchrone)

3. **API REST** (`/api/v1/notifications`) :
   - `GET /notifications/unread-count` : Nombre de notifications non lues
   - `POST /notifications/mark-as-read/<id>` : Marquer comme lue
   - `POST /notifications/mark-all-read` : Tout marquer comme lu

4. **Gestionnaires d'evenements** :
   - Module `modules/notifications/events/` : ecoute les evenements de l'application et declenche les notifications appropriees

## Configuration

Configurer les variables email dans le fichier `.env` :

```env
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=user@example.com
MAIL_PASSWORD=votre_mot_de_passe
MAIL_DEFAULT_SENDER=noreply@example.com
```

## Utilisation

### Envoyer une notification

```python
from core.services.notifications.notification_service import NotificationService

# Envoyer une notification simple
notification = NotificationService.send_notification(
    user_id=1,
    title="Bienvenue",
    message="Bienvenue sur Budget App !",
    notification_type="info"
)

# Forcer l'envoi meme si les notifications sont desactivees
notification = NotificationService.send_notification(
    user_id=1,
    title="Notification importante",
    message="Ceci est une notification importante.",
    notification_type="warning",
    force_send=True
)

# Notification avec URL d'action et envoi email
notification = NotificationService.send_notification(
    user_id=1,
    title="Budget depasse",
    message="Votre budget Alimentation a depasse 90%.",
    notification_type="warning",
    action_url="/dashboard",
    send_email=True
)
```

### Creer une notification sans envoi

```python
from core.services.notifications.notification_service import NotificationService

notification = NotificationService.create_notification(
    user_id=1,
    title="Nouveau rapport",
    message="Votre rapport mensuel est disponible.",
    notification_type="info",
    action_url="/reports",
    metadata={"report_id": 42}
)
```

### Gerer les preferences de notification

```python
from core.services.notifications.notification_service import NotificationService

# Recuperer les preferences d'un utilisateur
prefs = NotificationService.get_notification_preferences(user_id=1)

# Mettre a jour les preferences
pref = NotificationService.update_notification_preferences(
    user_id=1,
    notification_type="transaction",
    email=True,
    push=False,
    frequency="daily"
)
```

### Gerer les notifications

```python
from core.services.notifications.notification_service import NotificationService

# Marquer une notification comme lue
NotificationService.mark_as_read(notification_id=1, user_id=1)

# Marquer toutes les notifications comme lues
count = NotificationService.mark_all_as_read(user_id=1)

# Recuperer le nombre de notifications non lues
unread_count = NotificationService.get_unread_count(user_id=1)

# Recuperer les notifications avec pagination
notifications = NotificationService.get_user_notifications(
    user_id=1,
    unread_only=True,
    limit=10,
    offset=0
)
```

## Types de notifications

| Type | Description |
|------|-------------|
| `info` | Information generale |
| `warning` | Avertissement (budget proche du seuil, etc.) |
| `error` | Erreur (echec d'import, etc.) |
| `success` | Confirmation (transaction creee, etc.) |

## Preferences par defaut

Lorsqu'aucune preference n'existe pour un type de notification, les parametres par defaut sont :

- Email : active
- Push : active
- SMS : desactive
- Frequence : immediate

## Tests

```bash
cd backend
pytest tests/ -k notification -v
```

## Securite

- Les notifications sont filtrees par `user_id` : un utilisateur ne peut voir que ses propres notifications
- Les preferences sont egalement liees a l'utilisateur
- L'envoi d'email est protege par un try/catch pour ne pas bloquer le flux applicatif
