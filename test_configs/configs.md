List of all configurations available in the project. Each configuration is defined in a separate file and can be used to set up different environments or scenarios for the application.

⚠️ All this configurations intend to be used for testing purposes. In the study version, configurations may be generated randomly.

Each container definition can set `cpuLimit` to control the CPU cap emitted in the generated Docker Compose file.

granularity :

- fine : each microservice is in its own service definition in the compose file, with its own resource limits and logs.
- medium : microservices are grouped into services with 1-4 microservices each, with shared resource limits and logs per service.
- coarse : all microservices are in a single service definition in the compose file, with shared resource limits and logs.

isolation :

- none : all microservices run in the same container, no isolation.
- medium : containers are defined per service (for medium granularity) or group 1-4 services, providing some isolation
- high : each services (coarse granularity, service run one microservice) run in its own container, providing high isolation but more overhead.

# Microservices dependency graph

There are 12 microservices in the application.

```mermaid
graph TD
    A[Microservice A]
    B[Microservice B]
    C[Microservice C]
    D[Microservice D]
    E[Microservice E]
    F[Microservice F]
    G[Microservice G]
    H[Microservice H]
    I[Microservice I]
    J[Microservice J]
    K[Microservice K]
    L[Microservice L]

    A --> H --> C
    A --> B --> C
    A --> G
    A --> E
    A --> I
    A --> J --> C
    J --> D --> E
    D --> K
    D --> F
    D --> L
    A --> F
```

# Configuration 1 : Monolithic Application, coarse granularity, no isolation

**File Name**: `1_monolithic.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph Container A
        subgraph Service A
            direction TD
            A[Microservice A]
            B[Microservice B]
            C[Microservice C]
            D[Microservice D]
            E[Microservice E]
            F[Microservice F]
            G[Microservice G]
            H[Microservice H]
            I[Microservice I]
            J[Microservice J]
            K[Microservice K]
            L[Microservice L]
        end
    end

    A --> H --> C
    A --> B --> C
    A --> G
    A --> E
    A --> I
    A --> J --> C
    J --> D --> E
    D --> K
    D --> F
    D --> L
    A --> F
```

# Configuration 2 : Microservices with medium granularity, no isolation

**File Name**: `2_microservices_medium_granularity.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph CA [Container A]
        direction TD
        subgraph SA [Service A]
            direction TD
            MA[Microservice A]
        end
        subgraph SB [Service B]
            direction TD
            MB[Microservice B]
            MC[Microservice C]
            MH[Microservice H]
        end
        subgraph SC [Service C]
            direction TD
            MG[Microservice G]
            MI[Microservice I]
            MJ[Microservice J]
            MD[Microservice D]
        end
        subgraph SD [Service D]
            direction TD
            ME[Microservice E]
            MF[Microservice F]
            MK[Microservice K]
            ML[Microservice L]
        end
    end

    MA --> MH --> MC
    MA --> MB --> MC
    MA --> MG
    MA --> ME
    MA --> MI
    MA --> MJ --> MC
    MJ --> MD --> ME
    MD --> MK
    MD --> MF
    MD --> ML
    MA --> MF
```

# Configuration 3 : Microservices with fine granularity, no isolation

**File Name**: `3_microservices_fine_granularity.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph CA [Container A]
        direction TD
        subgraph SA [Service A]
            MA[Microservice A]
        end
        subgraph SB [Service B]
            MB[Microservice B]
        end
        subgraph SC [Service C]
            MC[Microservice C]
        end
        subgraph SD [Service D]
            MD[Microservice D]
        end
        subgraph SE [Service E]
            ME[Microservice E]
        end
        subgraph SF [Service F]
            MF[Microservice F]
        end
        subgraph SG [Service G]
            MG[Microservice G]
        end
        subgraph SH [Service H]
            MH[Microservice H]
        end
        subgraph SI [Service I]
            MI[Microservice I]
        end
        subgraph SJ [Service J]
            MJ[Microservice J]
        end
        subgraph SK [Service K]
            MK[Microservice K]
        end
        subgraph SL [Service L]
            ML[Microservice L]
        end
    end

    MA --> MH --> MC
    MA --> MB --> MC
    MA --> MG
    MA --> ME
    MA --> MI
    MA --> MJ --> MC
    MJ --> MD --> ME
    MD --> MK
    MD --> MF
    MD --> ML
    MA --> MF
```

# Configuration 4 : Microservices with medium granularity, with medium isolation

**File Name**: `4_microservices_medium_granularity_isolation.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph CA [Container A]
        direction TD
        subgraph SA [Service A]
            direction TD
            MA[Microservice A]
        end
    end
    subgraph CB [Container B]
        direction TD
        subgraph SB [Service B]
            direction TD
            MB[Microservice B]
            MC[Microservice C]
            MH[Microservice H]
        end
    end
    subgraph CC [Container C]
        direction TD
        subgraph SC [Service C]
            direction TD
            MG[Microservice G]
            MI[Microservice I]
            MJ[Microservice J]
            MD[Microservice D]
        end
    end
    subgraph CD [Container D]
        direction TD
        subgraph SD [Service D]
            direction TD
            ME[Microservice E]
            MF[Microservice F]
            MK[Microservice K]
            ML[Microservice L]
        end
    end


    MA --> MH --> MC
    MA --> MB --> MC
    MA --> MG
    MA --> ME
    MA --> MI
    MA --> MJ --> MC
    MJ --> MD --> ME
    MD --> MK
    MD --> MF
    MD --> ML
    MA --> MF
```

# Configuration 5 : Microservices with fine granularity, with medium isolation

**File Name**: `5_microservices_fine_granularity_isolation.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph CA [Container A]
        direction TD
        subgraph SA [Service A]
            direction TD
            MA[Microservice A]
        end
    end
    subgraph CB [Container B]
        direction TD
        subgraph SB [Service B]
            direction TD
            MB[Microservice B]
        end
        subgraph SC [Service C]
            direction TD
            MC[Microservice C]
        end
        subgraph SH [Service H]
            direction TD
            MH[Microservice H]
        end
    end
    subgraph CC [Container C]
        direction TD
        subgraph SG [Service G]
            direction TD
            MG[Microservice G]
        end
        subgraph SI [Service I]
            direction TD
            MI[Microservice I]
        end
        subgraph SJ [Service J]
            direction TD
            MJ[Microservice J]
        end
        subgraph SD [Service D]
            direction TD
            MD[Microservice D]
        end
    end
    subgraph CD [Container D]
        direction TD
        subgraph SE [Service E]
            direction TD
            ME[Microservice E]
        end
        subgraph SF [Service F]
            direction TD
            MF[Microservice F]
        end
        subgraph SK [Service K]
            direction TD
            MK[Microservice K]
        end
        subgraph SL [Service L]
            direction TD
            ML[Microservice L]
        end
    end

    MA --> MH --> MC
    MA --> MB --> MC
    MA --> MG
    MA --> ME
    MA --> MI
    MA --> MJ --> MC
    MJ --> MD --> ME
    MD --> MK
    MD --> MF
    MD --> ML
    MA --> MF
```

# Configuration 6 : Microservices with fine granularity, with high isolation

**File Name**: `6_microservices_fine_granularity_high_isolation.config.json`

Microservices configuration :

```mermaid
graph TD
    subgraph CA [Container A]
        direction TD
        subgraph SA [Service A]
            direction TD
            MA[Microservice A]
        end
    end
    subgraph CB [Container B]
        direction TD
        subgraph SB [Service B]
            direction TD
            MB[Microservice B]
        end
    end
    subgraph CC [Container C]
        direction TD
        subgraph SC [Service C]
            direction TD
            MC[Microservice C]
        end
    end
    subgraph CD [Container D]
        direction TD
        subgraph SD [Service D]
            direction TD
            MD[Microservice D]
        end
    end
    subgraph CE [Container E]
        direction TD
        subgraph SE [Service E]
            direction TD
            ME[Microservice E]
        end
    end
    subgraph CF [Container F]
        direction TD
        subgraph SF [Service F]
            direction TD
            MF[Microservice F]
        end
    end
    subgraph CG [Container G]
        direction TD
        subgraph SG [Service G]
            direction TD
            MG[Microservice G]
        end
    end
    subgraph CH [Container H]
        direction TD
        subgraph SH [Service H]
            direction TD
            MH[Microservice H]
        end
    end
    subgraph CI [Container I]
        direction TD
        subgraph SI [Service I]
            direction TD
            MI[Microservice I]
        end
    end
    subgraph CJ [Container J]
        direction TD
        subgraph SJ [Service J]
            direction TD
            MJ[Microservice J]
        end
    end
    subgraph CK [Container K]
        direction TD
        subgraph SK [Service K]
            direction TD
            MK[Microservice K]
        end
    end
    subgraph CL [Container L]
        direction TD
        subgraph SL [Service L]
            direction TD
            ML[Microservice L]
        end
    end

    MA --> MH --> MC
    MA --> MB --> MC
    MA --> MG
    MA --> ME
    MA --> MI
    MA --> MJ --> MC
    MJ --> MD --> ME
    MD --> MK
    MD --> MF
    MD --> ML
    MA --> MF
```
