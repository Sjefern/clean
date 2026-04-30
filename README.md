# Clean - Bilvaske bestillingssystem

Et Flask-basert system for bestilling og administrering av bilvask. Løsningen har to roller:

**Bileier** kan registrere seg, logge inn, bestille vask og se status på egne bestillinger.
**Vaskeekspert** kan se ventende bestillinger, akseptere eller avslå dem, og følge opp planlagte oppdrag.

## Hovedfunksjoner

- forsiden/index.html som selger inn god bilvask.
- Sentrerte login- og registreringssider.
- Eget dashboard for bileier med pakkekort og bestillingshistorikk.
- Eget dashboard for vaskeekspert med oppgavekort og tabellvisninger.
- Prisberegning basert på biltype og valgt behandling.
- ett ok design med bedre lesbarhet, kontrast og responsiv layout.


## Filstruktur

```text
/var/www/clean/
├── app.py
├── forms.py
├── db_config.py
├── app.wsgi
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── bileier_h.html
│   ├── vasker_h.html
│   ├── bestilling.html
│   ├── mine_bestillinger.html
│   ├── kunder.html
│   └── planlagt_oppdrag.html
├── static/
│   ├── style/style.css
│   └── js/bestilling.js
└── env/
```

## Teknologi

- Flask for webapplikasjonen.
- Jinja2 for templating.
- MySQL Connector/Python for databasekoblinger.
- Flask-WTF og WTForms for skjemaer.
- CSS med variabler, gradients og responsive grid/flex-layouter.

## Databaser

Applikasjonen bruker to databaser:

### `clean`
Lagrer brukerdata i tabellen `brukere`.

- `navn`
- `brukernavn` / e-post
- `passord` som hash
- `adresse`, som i praksis brukes til å lagre rolle: `bileier` eller `vaskeekspert`

### `bestillinger`
Lagrer bestillinger, pris og status.

Vanlige felt:

- `navn`
- `epost`
- `biltype`
- `tjeneste`
- `bestillingsdato`
- `bestillingstid`
- `pris`
- `merknad`
- `status`
- `vaskeekspert_email`


## Skjemaer

- **RegisterForm**: rolle, navn, e-post og passord.
- **LoginForm**: e-post og passord.
- **BookingForm**: behandling, biltype, dato, tid og merknad.

## Design og tilgjengelighet

- Fast toppmeny med CLEANRIDE-branding og «Hjem»-lenke for innloggede brukere.
- Sentrerte kort- og skjemaoppsett for bedre fokus.
- Blå fargepalett med høy kontrast.
- Minimum 16px basisfont, god linjeavstand.

## Oppsett og kjøring

```bash
source env/bin/activate
flask run
```

## Sikkerhet

- Passord lagres som hash med `werkzeug.security`.
- Hardkodet `secret_key`..


## Kort arbeidsflyt

1. Bruker registrerer seg som bileier eller vaskeekspert.
2. Bruker logger inn.
3. Bileier oppretter bestilling.
4. Vaskeekspert vurderer bestillingen.

## TO DO

Jeg har masse jeg vil implementere til nettsiden, rakk ikke å gjøre alt jeg hadde lyst til.

### To do list

1. Avbestilling eller endring av bestilling
2. Tydelig bekreftelsesside etter at en bestilling er sendt inn
3. E-postvarsler ved registrering, ny bestilling, godkjenning og avslag
4. Admin-side for å endre priser, tjenester og biltyper uten å redigere kode
5. Søk og filtrering i lister over bestillinger
6. Mulighet for å se ledige tider og hindre dobbeltbooking
7. Kontakt- eller hjelpeside
8. Personvern- og vilkårsside
9. Logg eller historikk over hva som har skjedd med en bestilling
10. Bedre feilhåndtering med tydelige meldinger når noe går galt
11. lage ordentlig fin styling
12. Mulighet for å deaktivere eller skjule tjenester som ikke lenger skal brukes
13. Mulighet for brukeren å oppdatere egen profil, som navn og e-post
14. Mobilvennlig finjustering hvis du vil gjøre den skikkelig solid på små skjermer
