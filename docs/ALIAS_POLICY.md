# Alias policy

## Sources

- Upstream fields are kept separate from aliases.
- Spreadsheet `キャラ` の `略称` is imported by stable character ID.
- Future manual aliases are edited directly in the master-data spreadsheet.

## Dynamic aliases

Only a trailing variant suffix in parentheses is removed:

```text
スズナ（サマー） -> スズナ
スズナ (Summer) -> スズナ
```

Other abbreviations are never guessed.

既存の `aliases` が空の場合だけ動的aliasを追加し、既存aliasは変更・削除しない。

## Ambiguity

An alias may match multiple IDs. It is retained in the generated data and reported in `alias_collisions`. Consumer code must use candidate lookup for ambiguous aliases; it must not select the first result.
