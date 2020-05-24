
    const modal = document.getElementById("navigation-modal");

    window.addEventListener("click",function(event) {

      if(event.target == modal) modal.style.display = "none";
    });

    function showModal(){
        modal.style.display = "block";
    }

    function closeModal(){
        modal.style.display = "none";
    }
    let nodes;
    let focus;
    let margin = 50,
        outerDiameter = window.innerHeight,
        innerDiameter = outerDiameter - margin - margin;

    // Scales
    let x = d3.scaleLinear()
        .range([0, innerDiameter]);
    let y = d3.scaleLinear()
        .range([0, innerDiameter]);

    //Scale for color-coding folder-bubbles
    let color = d3.scaleLinear()
        .domain([-1, 5])
        .range(["hsl(185,60%,99%)", "hsl(187,40%,80%)"])
        .interpolate(d3.interpolateHcl);

    //Scale for color-coding by fraction of old code
    let color_flag_code = d3.scaleSequential()
        .domain([1, 0])
        .interpolator(d3.interpolateRdYlGn);

    //Scale for color-coding by number of authors
    let color_flag_authors = d3.scaleThreshold()
        .domain([2, 3])
        .range(["#E15759", "#EDC948", "#59A14F"]);


    // Build SVG Container
    var svg = d3.select("div#viz-container").append("svg")
        .attr("width", outerDiameter)
        .attr("height", outerDiameter)
        .append("g")
        .attr("class", "svg-container")
        .attr("transform", "translate(" + margin + "," + margin + ")");


    // Build legend
    let keys_authors = [
        {label: "1 Autor", value: 1},
        {label: "2 Autoren", value: 2},
        {label: "2+ Autoren", value: 3}
    ];

    let legend_svg = svg
        .append("svg")
        .attr("class", "legend-box");

    let legend_items_container = legend_svg
        .append("g")
        .attr("transform", `translate(${(outerDiameter - margin) * 0.8},${margin})`);

    let legend_items = legend_items_container.selectAll("legend-items")
        .data(keys_authors)
        .enter()
        .append("g");

    let legend_dots = legend_items.insert("circle")
        .attr("class", "legend-dot")
        .attr("cx", 10)
        .attr("cy", (d, i) => (10 + i * 25))
        .attr("r", 10)
        .style("fill", (d, i) => color_flag_authors(d.value))
        .on("click", function (d) {
            d3.select(this).classed("dot-selected", d3.select(this).classed("dot-selected") ? false : true);

            selection_values = [];
            d3.selectAll(".legend-dot").filter(".dot-selected").each((d) => selection_values.push(d.value));

            d3.selectAll(".node--leaf").classed("filtered", function (d) {
                return selection_values.includes(d.data.author_count) || selection_values.length === 0 ? false : selection_values.includes(3) && d.data.author_count > 3 ? false : true;
            });

            d3.selectAll("circle.node--leaf").filter(".filtered")
                .transition(1000).attr("r", 0);

            d3.selectAll("circle.node:not(.filtered)").transition(1000).attr("r", (d) => d.r);

            d3.selectAll("node-label .node--leaf").filter(".filtered")
                .class("display", "none");

        });

    let legend_labels = legend_items
        .insert("text")
        .attr("class", "legend-label")
        .attr("x", 25)
        .attr("y", (d, i) => (10 + i * 25))
        .style("fill", (d, i) => color_flag_authors(d.value))
        .html((d, i) => d.label);
    // Build Legend

    d3.json("./files/flare.json").then(function (root, error) {
        let current_depth = 0;
        focus = root;
        var pack = d3.pack().padding(5).size([innerDiameter, innerDiameter]);
        nodes = pack(d3.hierarchy(root)
            .sum(d => d.size)).descendants();
        root_node = nodes[0];

        d3.select(window).on("click", function () {
            zoom(root_node);
        });

        recalculateTextPaths(1);

        svg.append("g").selectAll("circle")
            .data(nodes)
            .enter().append("circle")
            .attr("class", function (d) {
                return d.parent ? d.children ? "node" : "node node--leaf" : "node node--root";
            })
            .attr("transform", function (d) {
                return "translate(" + d.x + "," + d.y + ")";
            })
            .attr("r", function (d) {
                return d.r;
            })
            .style("fill", function (d) {
                return d.children ? color(d.depth) : color_flag_authors(d.data.author_count);
            })
            .on("click", function (d) {
                if(d3.event.altKey){
                    return zoom(d.parent);
                }
                if(d3.event.ctrlKey || d3.event.metaKey){
                    return zoom(root_node);
                }
                return zoom(focus === d ? root_node : d);
            })
            .append("title").html(function (d) {
            if (d.children) {
                return `Lines of Code: ${d.value}` + "\n" + `Pfad: ${filepath(d)}`;
            } else {
                return `Lines of Code: ${d.value}` + "\n" + `Pfad: ${filepath(d)}` + "\n" + `Anzahl Autoren: ${d.data.author_count || "Nicht verfügbar"}` + "\n" + `Anteil alter Code (%) : ${d.data.fraction_of_lines_older_6_months}` + "\n" + `Autor(en): \n\t${d.data.authors ? d.data.authors.split(",").join("\n\t") : "Nicht verfügbar"}`;
            }
        });

        d3.select("#selection_coloring").on("change", function (e) {
            var selection = d3.select(this).property("value");
            //toggleLegend(selection);
            if (selection === "code") {
                d3.selectAll("circle.node").style("fill", function (d) {
                    return d.children ? color(d.depth) : color_flag_code(d.data.fraction_of_lines_older_6_months);
                });
            } else {
                d3.selectAll("circle.node").style("fill", function (d) {
                    return d.children ? color(d.depth) : color_flag_authors(d.data.author_count);
                });
            }

        });

        svg.append("g").selectAll("text")
            .data(nodes)
            .enter().append("text")
            .attr("class", function (d) {
                return d.data.parent ? d.data.children ? "node-label" : "node-label node--leaf" : "node-label node--root";
            })
            .style("fill-opacity", function (d) {
                // return d.depth <= 1 ? 1 : 0;
                return ((d.depth === current_depth || d.depth === current_depth+1) ? 1 : 0);
                //return d.parent === root_node ? 1 : 0;
            })
            .style("display", function (d) {
                return ((d.depth === current_depth || d.depth === current_depth+1) ? null : "none");
                //return d.parent === root_node ? null : "none";
            })
            .attr("transform", (d, i) => "translate(" + d.x + "," + d.y + ")")
            .append("textPath")
            .attr("xlink:href", (d, i) => "#curve_" + i)
            .attr("startOffset", "25%")
            .text(function (d) {
                return d.data.name;
            });

        function zoom(d, i) {
            var focus0 = focus;
            focus = d;
            current_depth = d.depth;
            var k = innerDiameter / d.r / 2;
            x.domain([d.x - d.r, d.x + d.r]);
            y.domain([d.y - d.r, d.y + d.r]);
            d3.event.stopPropagation();


            // Redraw defs for text-paths
            recalculateTextPaths(k);

            //Hide legend-box if zoomed in
            d3.select(".legend-box").attr("display", () => focus === root_node ? "inline" : "none");

            //transform all nodes & labels with the current x/y-domain (zoom)
            var transition = d3.selectAll("text.node-label, circle.node:not(.filtered)").transition().duration(750)
                .attr("transform", function (d) {
                    return "translate(" + x(d.x) + "," + y(d.y) + ")";
                });

            transition.filter("circle.node:not(.filtered)")
                .attr("r", function (d) {
                    return k * d.r;
                });


            transition.filter("text:not(.filtered)")
                // .filter(function (d) {
                //     return d === focus || d.parent === focus || d.parent === focus0 || d === focus0;
                // })
                .style("fill-opacity", function (d) {
                    return ((d.depth === current_depth || d.depth === current_depth+1) ? 1 : 0);
                    //return d === focus ? 1 : d.parent ? 1 : 0;
                })
                .style("display", function (d) {
                return ((d.depth === current_depth || d.depth === current_depth+1) ? null : "none");
                //return d.parent === root_node ? null : "none";
                });
                // .each("end", function (d) {
                //     (d.depth === current_depth || d.depth === current_depth+1)?this.style.display = "inline" : this.style.display="none";
                //     //d === focus ? this.style.display = "inline" : d.parent === focus ? this.style.display = "inline" : this.style.display = "none";
                // });

        }//zoom


        //Utility Functions
        function toggleLegend(selection) {
            if (selection === "code") {
                legend_items_container.style("display", "none");
            } else {
                legend_items_container.style("display", "inline");
            }
        }

        function recalculateTextPaths(scaleFactor) {
            d3.select("defs").remove();
            var textpaths = d3.select(".svg-container").append("defs");
            textpaths.selectAll("text-path")
                .data(nodes).enter()
                .append("path")
                .attr("id", (d, i) => "curve_" + i)
                .attr("d", (d, i) => arcGenerator(d, scaleFactor));
        }

        function filepath(d) {
            var file_paths = [d.data.name];
            while (d.parent) {
                d = d.parent;
                file_paths.push(d.data.name);
            }
            return file_paths.reverse().join("/");
        }

        function arcGenerator(d, scaleFactor) {
            var arcFunc = d3.arc().startAngle(1.5 * Math.PI).endAngle(0.5 * Math.PI).innerRadius(scaleFactor * d.r).outerRadius(scaleFactor * d.r);
            return arcFunc();
        }
    });

    d3.select(self.frameElement).style("height", outerDiameter + "px");
