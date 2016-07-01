# wall-it

## Dépendances :

Flask :

```
 $ pip install flask
```

Connexion à Google :

```
 $ pip install httplib2
 $ pip install oauth2client
```

Pygal :

```
 $ pip install pygal
```

Initialisation de la Bdd :

```
 $ sqlite3 /tmp/wallit.db < schema.sql
```

NB: il se peut que la liste des contacts des popups d'ajout et de modification ne soit pas complète. Dans ce cas, il faut les ajouter dans vos contacts Google. (GMail > Contacts > Annuaire > tout sélectionner > ajouter à mes contacts)
