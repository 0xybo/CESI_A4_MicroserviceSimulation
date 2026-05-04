# Architecture 7 - 2_microservices_medium_granularity

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
        end
        subgraph ServiceB [ServiceB]
            direction TD
            MB[Microservice B]
            MC[Microservice C]
            MH[Microservice H]
        end
        subgraph ServiceC [ServiceC]
            direction TD
            MG[Microservice G]
            MI[Microservice I]
            MJ[Microservice J]
            MD[Microservice D]
        end
        subgraph ServiceD [ServiceD]
            direction TD
            ME[Microservice E]
            MF[Microservice F]
            MK[Microservice K]
            ML[Microservice L]
        end
    end

    MA --> MB
    MA --> ME
    MB --> MI
    MB --> MK
    MC --> MH
    ME --> MF
    ME --> MH
    ME --> MJ
    MG --> ML
    MH --> MD
    MI --> MC
    MI --> MD
    MI --> MH
    MK --> MG
    ML --> MJ
```
