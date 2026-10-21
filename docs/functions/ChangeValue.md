# ChangeValue(name: string, value: any)

Switches a feature on or off by name. Names follow the executor's own menu, for example
`[A] Auto collect` or `[A] Farm: Break delay`. Values can be a boolean, a number, or a hex
colour such as `0xFFFFFFFF`.

An unknown name changes nothing and raises no error. Use `GetValue` to confirm a feature
exists before relying on it.

Parameters
- `name: string`: feature or setting name.
- `value: any`: new value, boolean, number, string, or hex.

Returns
- Nothing.

Example (Lua)
```lua
ChangeValue('[A] Auto collect', true)
ChangeValue('[M] Network text color', 0xFFFFFFFF)
ChangeValue('[A] Farm: Break delay', 300)
```

Note
- `GetValue(name)` reads a feature back; an unknown name returns `nil`.
