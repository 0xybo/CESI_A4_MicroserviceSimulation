# Architecture 3 - 1_monolithic

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

    MA --> MB
    MA --> MD
    MA --> MH
    MB --> ML
    MD --> MF
    ME --> MC
    ME --> MG
    ME --> MI
    MF --> MJ
    MF --> MK
    MH --> MG
    MJ --> ME
    MJ --> MI
    MK --> MG
    MK --> MI
```
