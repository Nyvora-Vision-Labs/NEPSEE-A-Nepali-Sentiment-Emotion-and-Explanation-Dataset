# Nepali Twitter Accounts — Current Affairs Sentiment Corpus Sources

A curated list of 20 X (Twitter) accounts for scraping Nepali-language tweets on politics, governance, and current affairs. Accounts are grouped by category to help balance topical diversity in the final dataset.

---

## 1. Politicians & Elected Officials

Primary source for policy commentary, party rhetoric, and politically-charged sentiment — expect strong opinion density here, similar to how L3CubeMahaSent leaned on Maharashtrian political personalities.

| Name               | Handle                                                  | Role                                                                          |
| ------------------ | ------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Balen Shah         | [@ShahBalen](https://twitter.com/ShahBalen)             | Former Mayor of Kathmandu, structural engineer, independent political voice   |
| Gagan Thapa        | [@thapagk](https://twitter.com/thapagk)                 | General Secretary, Nepali Congress; MP                                        |
| Rabi Lamichhane    | [@hamrorabi](https://twitter.com/hamrorabi)             | Chairperson, Rastriya Swatantra Party (RSP); former Deputy PM & Home Minister |
| Swarnim Wagle      | [@SwarnimWagle](https://twitter.com/SwarnimWagle)       | Vice-Chair, RSP; economist, MP                                                |
| Baburam Bhattarai  | [@brb1954](https://twitter.com/brb1954)                 | Former Prime Minister; Chairman, Socialist Party (Naya Shakti)                |
| Sher Bahadur Deuba | [@SherBDeuba](https://twitter.com/SherBDeuba)           | Former Prime Minister; President, Nepali Congress                             |
| KP Sharma Oli      | [@kpsharmaoli](https://twitter.com/kpsharmaoli)         | Former Prime Minister; Chairman, CPN(UML)                                     |
| Ram Kumari Jhakri  | [@Jhakri_didi](https://twitter.com/Jhakri_didi)         | Former Minister of Urban Development; CPN(UML)                                |
| Binod Chaudhary    | [@BinodKChaudhary](https://twitter.com/BinodKChaudhary) | MP; Chairman, Chaudhary Group; economic/policy commentator                    |

**Coverage:** spans the major parties — Nepali Congress, CPN(UML), RSP, Socialist Party — plus one independent (Balen Shah). Good ideological spread, which matters for reducing partisan skew in your sentiment labels.

---

## 2. Journalists & Media Figures

Expect a mix of analytical/critical commentary, event reporting, and op-ed style content — useful for more measured, "neutral"-leaning sentiment as a counterweight to the politicians' category.

| Name               | Handle                                                | Role                                                                |
| ------------------ | ----------------------------------------------------- | ------------------------------------------------------------------- |
| Sudheer Sharma     | [@sudheerktm](https://twitter.com/sudheerktm)         | Journalist; former Editor-in-Chief, Kantipur National Daily         |
| Rabindra Mishra    | [@RabindraMishra](https://twitter.com/RabindraMishra) | Former Head, BBC Nepali; Senior VP, Rastriya Prajatantra Party      |
| Kanak Mani Dixit   | [@KanakManiDixit](https://twitter.com/KanakManiDixit) | Writer; publisher, Himal Khabar Patrika                             |
| Kunda Dixit        | [@kundadixit](https://twitter.com/kundadixit)         | Journalist, Nepali Times                                            |
| Narayan Wagle      | [@narayanwagle](https://twitter.com/narayanwagle)     | Journalist, novelist (Palpasa Café); Setopati                       |
| Tanka Dahal        | [@shishirdahal](https://twitter.com/shishirdahal)     | Independent political commentator, content creator/YouTuber         |
| Vijay Kumar Panday | [@Vijaykumarko](https://twitter.com/Vijaykumarko)     | Writer, TV host, social/political commentator                       |
| Bhusan Dahal       | [@DahalTbd](https://twitter.com/DahalTbd)             | Media personality; host, socio-political dialogue show (bRAVOdELTA) |
| Rishi Dhamala      | [@RishiDhamala](https://twitter.com/RishiDhamala)     | Former politician; prominent talk-show journalist                   |

**Coverage:** blends legacy print journalism (Kantipur, Himal, Nepali Times), broadcast (BBC Nepali), and newer digital/YouTube-native political commentary — good for capturing generational shifts in tone and vocabulary.

---

## 3. Activists & Social Commentators

| Name           | Handle                                                  | Role                                                                           |
| -------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Mahabir Pun    | [@MahabirPun](https://twitter.com/MahabirPun)           | Social activist; Chair, National Innovation Center; rural development advocate |
| Nirmala Dhakal | [@Nirmaladhakal44](https://twitter.com/Nirmaladhakal44) | Sociologist, social media commentator                                          |

**Coverage:** civil-society and academic-adjacent voices, useful for balancing the corpus away from party-line rhetoric.

---

## Summary Table

| Category                        | Count  | % of Total |
| ------------------------------- | ------ | ---------- |
| Politicians & Elected Officials | 9      | 45%        |
| Journalists & Media Figures     | 9      | 45%        |
| Activists & Social Commentators | 2      | 10%        |
| **Total**                       | **20** | **100%**   |

---

## Notes for Dataset Construction

- **Political balance:** the politician group spans 4+ parties across the ideological spectrum (Nepali Congress, CPN-UML, RSP, Socialist Party, independent) — worth tracking party affiliation as metadata so you can later check for annotation bias toward/against particular parties.
- **Topical diversity:** journalists and activists should help pull in content beyond pure party politics — governance critique, social issues, cultural commentary — which will make your emotion labels (not just sentiment) more varied than a politician-only corpus would.
- **Verification before scraping:** confirm each handle is still active and not suspended/renamed, especially given the account/platform disruptions tied to Nepal's 2025 social media restrictions — a dead handle mid-scrape will silently cut your data collection short for that source.
- **Temporal metadata:** given the September 2025 platform block and subsequent political transition (Balen Shah becoming PM in 2026), consider tagging tweets with pre-ban / post-ban timestamps — this could become a natural analysis axis in your paper (similar to NepEMO's temporal trend analysis), and also helps you explain any gaps in your scraped timeline.

2026 Favikon ranking and Look at Follower count.
