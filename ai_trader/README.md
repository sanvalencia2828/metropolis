# ai_trader

Capa de datos para recolectar mercado en GMGN, guardar snapshots y armar features.

```bash
pip install -r requirements.txt
python app.py chains
python app.py init-db
python app.py collect --chain sol --limit 20
pytest
```

`config/` ya define settings y chains. Redis es opcional: el cache cae a memoria si no hay servidor.
