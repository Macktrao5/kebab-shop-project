def carrello_context(request):
    carrello = request.session.get('carrello', {})
    quantita_totale = 0
    
    if isinstance(carrello, dict):
        for item in carrello.values():
            if isinstance(item, dict):
                quantita_totale += int(item.get('quantita', 1))
    elif isinstance(carrello, list):
        for item in carrello:
            if isinstance(item, dict):
                quantita_totale += int(item.get('quantita', 1))

    return {
        'carrello_quantita_totale': quantita_totale
    }