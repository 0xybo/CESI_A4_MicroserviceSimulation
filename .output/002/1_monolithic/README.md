# Architecture 2 - 1_monolithic

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

    MA --> MI
    MB --> ML
    MC --> MB
    MC --> MF
    MC --> MG
    MC --> MK
    MH --> MD
    MH --> ME
    MI --> MC
    MI --> MH
    MI --> MJ
    MI --> ML
    MJ --> ME
    MJ --> ML
    MK --> MD
```
