# Bibliotekos valdymo sistema naudojant NoSQL duomenų bazes

## Projekto aprašymas

Projektas atliktas Vilniaus universiteto Matematikos ir informatikos fakulteto nereliacinių duomenų bazių kurso metu.

Projekto tikslas – sukurti bibliotekos valdymo sistemą, naudojant skirtingas NoSQL duomenų bazių technologijas ir jas integruojant į vieną aplikaciją.

Laboratorinių darbų metu buvo kuriama ir palaipsniui plečiama Python ir Flask pagrindu veikianti REST API aplikacija. Pradžioje realizuotos pagrindinės bibliotekos valdymo funkcijos naudojant MongoDB, o vėliau sistema papildyta duomenų spartinimo, veiksmų registravimo, knygų rekomendavimo ir analitikos galimybėmis.

## Darbe naudota

| Pavadinimas | Paskirtis |
|---|---|
| Python | Pagrindinė programavimo kalba |
| Flask | REST API kūrimas |
| MongoDB | Bibliotekos duomenų saugojimas ir valdymas |
| Redis | Duomenų spartinimas (*caching*) |
| Apache Cassandra | Sistemos veiksmų žurnalų saugojimas |
| Neo4j | Grafų duomenų bazė knygų rekomendacijoms |
| ClickHouse | Analitinių duomenų saugojimas ir analizė |
| JWT | Naudotojų autentifikavimas ir autorizavimas |
| Swagger / Flasgger | API dokumentacija ir testavimas |

## Laboratoriniai darbai

### 1. MongoDB – bibliotekos valdymo sistema

Pirmajame laboratoriniame darbe sukurta REST API aplikacija, naudojanti MongoDB dokumentinę duomenų bazę.

Įgyvendintos funkcijos:
- Knygų ir jų egzempliorių valdymas.
- Skaitytojų ir bibliotekos filialų duomenų valdymas.
- Knygų paieška ir filtravimas.
- Knygų rezervavimas, išdavimas ir grąžinimas.
- Naudotojų autentifikavimas ir prieigos teisių valdymas.
- Duomenų agregavimo užklausos.

Duomenų pavyzdžiai pateikiami `1_MongoDB/Duomenys` aplanke JSON formatu.

### 2–3. Redis ir Apache Cassandra – spartinimas ir veiksmų registravimas

Ankstesnė bibliotekos valdymo sistema papildyta dviem NoSQL duomenų bazėmis.

**Redis** naudojama dažnai pasiekiamų duomenų spartinimui, siekiant sumažinti pasikartojančių užklausų į MongoDB skaičių.

**Apache Cassandra** naudojama sistemoje atliekamų veiksmų žurnalams saugoti. Taip pat realizuotos API užklausos, skirtos žurnalų duomenims peržiūrėti.

### 4. Neo4j – knygų rekomendacijų sistema

Bibliotekos valdymo sistema papildyta Neo4j grafų duomenų baze.

Įgyvendintas duomenų sinchronizavimas su Neo4j ir knygų rekomendavimo funkcionalumas, leidžiantis analizuoti ryšius tarp skaitytojų ir knygų bei generuoti rekomendacijas.

### 5. NoSQL duomenų bazių integracija ir analitika

Paskutiniame laboratoriniame darbe integruotos visos anksčiau naudotos duomenų bazės: MongoDB, Redis, Apache Cassandra ir Neo4j. Papildomai įtraukta ClickHouse analitinė duomenų bazė.

Realizuotas duomenų sinchronizavimas iš MongoDB ir Cassandra į ClickHouse bei analitinės API užklausos, skirtos bibliotekos veiklos duomenims analizuoti.

## Projekto struktūra

```text
Bibliotekos_duomenu_baze/
│
├── 1_MongoDB/
│   ├── Biblioteka/
│   │   ├── app.py
│   │   ├── db.py
│   │   ├── routes/
│   │   └── utils/
│   └── Duomenys/
│       ├── books.json
│       ├── branches.json
│       ├── copies.json
│       ├── reservations.json
│       └── users.json
│
├── 2_Redis_Cassandra/
│   └── Biblioteka/
│       ├── app.py
│       ├── routes/
│       └── utils/
│
├── 3_Neo4J/
│   └── Biblioteka/
│       ├── app.py
│       ├── routes/
│       └── utils/
│
├── 4_Integracijos/
│   └── Biblioteka/
│       ├── app.py
│       ├── routes/
│       └── utils/
│
└── README.md
```

Kiekviename laboratorinio darbo aplanke pateikiama atitinkama bibliotekos valdymo sistemos versija.

- `app.py` – pagrindinis Flask aplikacijos failas.
- `routes/` – REST API maršrutai ir užklausų apdorojimas.
- `utils/` – pagalbinės funkcijos, duomenų bazių jungtys ir integracijos.
- `Duomenys/` – pradiniai bibliotekos duomenys JSON formatu.

## API dokumentacija

REST API dokumentacijai naudojamas Swagger, leidžiantis peržiūrėti ir testuoti realizuotas užklausas.

Paleidus tinkamai sukonfigūruotą aplikaciją, API dokumentacija pasiekiama adresu:

`http://127.0.0.1:5000/apidocs/`

## Pastabos

Projektas sukurtas mokymosi tikslais. Naudojami bibliotekos duomenys yra mokomieji.

Konfigūracijos failai `config.py`, kuriuose saugomi duomenų bazių prisijungimo nustatymai, į viešą repozitoriją neįtraukiami.

Norint paleisti projektą lokaliai, būtina sukonfigūruoti atitinkamų duomenų bazių prisijungimus ir įdiegti reikalingas Python bibliotekas.
