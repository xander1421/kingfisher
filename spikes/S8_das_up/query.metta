!(import! &self das)
!(bind! &das (new-das! (localhost:52000-52099) (localhost:40002)))
!(match &das (Similarity "human" $S) ($S))
!(match &das (Inheritance $X "mammal") ($X))
