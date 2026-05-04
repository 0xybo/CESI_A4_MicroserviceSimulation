# Architecture 6 - 4_microservices_medium_granularity_isolation

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
