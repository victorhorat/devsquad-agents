# Exemplos reais de uso

Registro vivo de vezes que o `devsquad-agents` foi usado pra construir de verdade os outros projetos do portfólio — comando exato, o que foi passado pra ele, o que ele decidiu sozinho, e o resultado. Cada entrada é um run real, sem edição manual do código gerado.

---

## food-order-agent — módulo de carrinho de compras

Rodado a partir do `devsquad-agents` apontando pro workspace do segundo projeto do portfólio:

```bash
devsquad run "modulo de carrinho de compras: uma classe Cart com os metodos add_item(item_id: str, nome: str, preco: float, quantidade: int) -> None (soma quantidade se o item_id ja existir), remove_item(item_id: str) -> bool (True se removeu, False se nao existia), list_items() -> list[dict] (cada item com item_id, nome, preco, quantidade, subtotal), subtotal() -> float (soma de todos os subtotais), e clear() -> None" \
  --workspace ../food-order-agent \
  --module src/foodagent/cart.py \
  --max-iterations 3
```

**O que passamos pra ele:** só a descrição da tarefa em linguagem natural, com a assinatura dos métodos esperados — nenhum código, nenhum exemplo de teste. O `--workspace`/`--module` dizem onde gravar se for aprovado.

**O que ele fez** (saída real do terminal):

```
🧭 Refiner (iter 0): Implementar um módulo de carrinho de compras com uma classe Cart que gerencia itens,
permitindo adicionar, remover, listar, calcular subtotal e limpar o carrinho.
👩‍💻 Coder (iter 1): Itens armazenados em dict interno preservando ordem de inserção. Validações rejeitam
bool como preço/quantidade por serem subclasses de int. Preço zero é aceito (não negativo).
🔍 QA (iter 1): aprovado

✅ Aprovado
Iterações: 1
```

O Coder decidiu por conta própria validar tipos de forma mais rígida do que o pedido original exigia — por exemplo, rejeitar `bool` como `preco`/`quantidade` (em Python, `isinstance(True, int)` é `True`, então sem essa checagem um `add_item("1", "x", True, 2)` passaria batido). E escreveu 11 casos de teste cobrindo carrinho vazio, acúmulo de quantidade no mesmo item, múltiplos itens, remoção existente/inexistente, limpar carrinho e as bordas de validação — tudo isso sem eu pedir caso a caso, só a partir da especificação de alto nível.

Arquivos gerados em `food-order-agent/src/foodagent/cart.py` e `test_cart.py` (link pro repositório assim que ele for publicado).
