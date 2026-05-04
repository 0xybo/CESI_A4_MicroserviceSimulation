# Architecture 3 - 4_microservices_medium_granularity_isolation

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
    end
    subgraph ContainerB [ContainerB]
        direction TD
        subgraph ServiceB [ServiceB]
            direction TD
            MB[Microservice B]
            MC[Microservice C]
            MH[Microservice H]
        end
    end
    subgraph ContainerC [ContainerC]
        direction TD
        subgraph ServiceC [ServiceC]
            direction TD
            MG[Microservice G]
            MI[Microservice I]
            MJ[Microservice J]
            MD[Microservice D]
        end
    end
    subgraph ContainerD [ContainerD]
        direction TD
        subgraph ServiceD [ServiceD]
            direction TD
            ME[Microservice E]
            MF[Microservice F]
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
