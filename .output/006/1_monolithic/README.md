# Architecture 6 - 1_monolithic

This folder was generated automatically.

- Config file: `config.json`
- Graph source: generated microservice dependencies

```mermaid
graph TD
    subgraph ContainerA [ContainerA]
        direction TD
        subgraph ServiceA [ServiceA]
            direction TD
            MA[Microservice A]
            MB[Microservice B]
            MC[Microservice C]
            MD[Microservice D]
            ME[Microservice E]
            MF[Microservice F]
            MG[Microservice G]
            MH[Microservice H]
            MI[Microservice I]
            MJ[Microservice J]
            MK[Microservice K]
            ML[Microservice L]
        end
    end

    MA --> MC
    MA --> MH
    MA --> MI
    MA --> MJ
    MA --> ML
    MC --> MK
    ME --> MB
    ME --> MF
    MF --> MI
    MG --> MD
    MH --> MB
    MJ --> MD
    ML --> ME
    ML --> MG
    ML --> MI
```
