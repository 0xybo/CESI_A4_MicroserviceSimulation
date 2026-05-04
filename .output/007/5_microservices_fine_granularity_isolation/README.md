# Architecture 7 - 5_microservices_fine_granularity_isolation

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
