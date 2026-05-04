# Architecture 8 - 5_microservices_fine_granularity_isolation

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
        end
        subgraph ServiceC [ServiceC]
            direction TD
            MC[Microservice C]
        end
        subgraph ServiceH [ServiceH]
            direction TD
            MH[Microservice H]
        end
    end
    subgraph ContainerC [ContainerC]
        direction TD
        subgraph ServiceG [ServiceG]
            direction TD
            MG[Microservice G]
        end
        subgraph ServiceI [ServiceI]
            direction TD
            MI[Microservice I]
        end
        subgraph ServiceJ [ServiceJ]
            direction TD
            MJ[Microservice J]
        end
        subgraph ServiceD [ServiceD]
            direction TD
            MD[Microservice D]
        end
    end
    subgraph ContainerD [ContainerD]
        direction TD
        subgraph ServiceE [ServiceE]
            direction TD
            ME[Microservice E]
        end
        subgraph ServiceF [ServiceF]
            direction TD
            MF[Microservice F]
        end
        subgraph ServiceK [ServiceK]
            direction TD
            MK[Microservice K]
        end
        subgraph ServiceL [ServiceL]
            direction TD
            ML[Microservice L]
        end
    end

    MA --> MF
    MA --> MJ
    MA --> MK
    MD --> MB
    MF --> MG
    MH --> MI
    MJ --> MB
    MJ --> MC
    MJ --> ME
    MK --> MB
    MK --> MD
    MK --> MH
    MK --> ML
    ML --> MB
    ML --> MD
```
