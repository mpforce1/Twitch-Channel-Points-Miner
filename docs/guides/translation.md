# Translation

The miner is capable of localising Event text via a system of key-value mappings in json files.
The files are located [here](/locales), please see the [English](/locales/en.json) translation for an example of how
translation is performed.

There are 3 types of localisation mappings provided: direct, plural, and optional. Additionally, all 3 can have substitutions.

## Substitutions

A substitution is a labelled segment of a string that the miner will swap out with a value. For example:

```json
"streamer_online": "{streamer} is Online!",
```

In this mapping, the string `{streamer}` will be replaced with the Streamer that has come online.

This might result in:

```text
streamer-01 is Online!
```

In some cases, mappings have multiple substitutions:

```json
"join_raid": "Joining raid from {streamer} to {target}!",
```

In this mapping, `{streamer}` will be replaced by the Streamer that has started the raid, and `{target}` will be
replaced with the Streamer that is being raided.

This might result in:

```text
Joining raid from streamer-01 to streamer-02!
```

## Direct

A direct translation is just a simple key-value pair:

```json
"STREAM_UP": "Stream Up",
```

## Plural

A plural translation uses the form:

```json
"key_name": {
  "singular": "A string containing {count} thing",
  "plural": "A string containing {count} things"
}
```

Where the `singular` and `plural` values contain a `{count}`. The count will be some number, based on the plural rules
for your locale. In `en` (and by default) the plural rule is singular when the count is 1 and plural otherwise. For
`fr`, the plural rule is singular when 0 or 1 and plural otherwise. More plural rules can be added in `Translator`.

A real example:

```json
"stream_view_count": {
  "singular": "{streamer} has {count} viewer",
  "plural": "{streamer} has {count} viewers"
}
```

The `stream_view_count` has a plural form that modifies `viewer` by appending an `s`. This might result in:

### Singular
```text
streamer-01 has 1 viewer
```

### Plural
```text
streamer-01 has 100 viewers
```

## Optional

An optional translation uses the form:

```json
"key_name": {
  "some": "Value when {substitution_key} exists",
  "none": "Value when it doesn't"
}
```

Where `some` contains an optional key (`substitution_key` in this case) when the key exists. `none` is the translation
when the value doesn't exist.

A real example:

```json
"gifter": {
  "some": "{value}",
  "none": "Anonymous"
}
```

In this case, the gifter of a gift sub can not exist in some cases. In the case the gifter exists, we just substitute it
directly. When they don't exist, we say `"Anonymous"`.

This might result in:

### Some

```text
gifter-01
```

### None

```text
Anonymous
```