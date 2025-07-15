/**
 * ResHub Academic Knowledge Map
 * Modern D3.js visualization for research connections
 */

// Main function to create the academic knowledge graph
function createSemanticGraph(data) {
  // Clear any existing graph container
  const container = document.getElementById('graph-container');
  container.innerHTML = '';

  // Extract dimensions from container
  const width = container.clientWidth;
  const height = container.clientHeight || 600;
  
  // Create SVG element with proper viewBox for responsiveness
  const svg = d3.select('#graph-container')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height])
    .attr('class', 'semantic-graph-svg');
  
  // Create a definitions section for clipPath (for circular avatars)
  const defs = svg.append('defs');
  
  // Add a subtle background grid
  const grid = svg.append('g')
    .attr('class', 'grid');
    
  // Create grid lines
  const gridSize = 40;
  const gridColor = '#f0f4f8';
  
  for (let x = 0; x < width; x += gridSize) {
    grid.append('line')
      .attr('x1', x)
      .attr('y1', 0)
      .attr('x2', x)
      .attr('y2', height)
      .attr('stroke', gridColor)
      .attr('stroke-width', 1);
  }
  
  for (let y = 0; y < height; y += gridSize) {
    grid.append('line')
      .attr('x1', 0)
      .attr('y1', y)
      .attr('x2', width)
      .attr('y2', y)
      .attr('stroke', gridColor)
      .attr('stroke-width', 1);
  }

  // Create groups for links and nodes
  const linkGroup = svg.append('g').attr('class', 'links');
  const nodeGroup = svg.append('g').attr('class', 'nodes');
  
  // Enhanced force simulation with more natural clustering
  const simulation = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.links)
      .id(d => d.id)
      .distance(d => d.source.group === 1 || d.target.group === 1 ? 140 : 100))
    .force('charge', d3.forceManyBody()
      .strength(d => d.group === 1 ? -600 : -300))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('x', d3.forceX(width / 2).strength(0.1))
    .force('y', d3.forceY(height / 2).strength(0.1))
    .force('collision', d3.forceCollide().radius(d => d.group === 1 ? 50 : 40));

  // Create links with gradient effect
  const link = linkGroup
    .selectAll('line')
    .data(data.links)
    .enter()
    .append('line')
    .attr('class', 'link')
    .attr('stroke-width', d => Math.sqrt(d.value) * 1.5 + 1)
    .attr('opacity', 0.7);

  // Create node groups
  const node = nodeGroup
    .selectAll('.node')
    .data(data.nodes)
    .enter()
    .append('g')
    .attr('class', d => d.group === 1 ? 'node node-central' : 'node')
    .call(d3.drag()
      .on('start', dragStarted)
      .on('drag', dragging)
      .on('end', dragEnded));
  
  // Create clipPaths for each node (for circular avatars)
  node.each(function(d, i) {
    const radius = d.group === 1 ? 30 : 20;
    defs.append('clipPath')
      .attr('id', 'clip-' + d.id)
      .append('circle')
      .attr('r', radius);
  });
  
  // Add subtle shadow effect for nodes
  node.append('circle')
    .attr('r', d => d.group === 1 ? 32 : 22)
    .attr('fill', '#000')
    .attr('opacity', 0.2)
    .attr('cx', 2)
    .attr('cy', 2);
    
  // Add circular container for avatar
  node.append('circle')
    .attr('r', d => d.group === 1 ? 30 : 20)
    .attr('class', 'node-avatar-container')
    .attr('fill', d => d.group === 1 ? '#4299e1' : '#90cdf4')
    .attr('stroke', '#fff')
    .attr('stroke-width', d => d.group === 1 ? 3 : 2);
  
  // Add avatar images
  node.append('image')
    .attr('xlink:href', d => d.avatar_url || `https://ui-avatars.com/api/?name=${d.name.replace(/ /g, '+')}&background=${d.group === 1 ? '4299e1' : '90cdf4'}&color=fff&size=60`)
    .attr('x', d => d.group === 1 ? -30 : -20)
    .attr('y', d => d.group === 1 ? -30 : -20)
    .attr('width', d => d.group === 1 ? 60 : 40)
    .attr('height', d => d.group === 1 ? 60 : 40)
    .attr('clip-path', d => `url(#clip-${d.id})`);
  
  // Add name labels below nodes
  node.append('text')
    .attr('class', 'node-label')
    .attr('dy', d => d.group === 1 ? 45 : 35)
    .attr('text-anchor', 'middle')
    .text(d => d.name.length > 15 ? d.name.substring(0, 15) + '...' : d.name)
    .style('font-weight', d => d.group === 1 ? '600' : '500');
  
  // Add similarity score badges for non-central nodes
  const similarityGroups = node.filter(d => d.group !== 1)
    .append('g')
    .attr('transform', d => `translate(15, -15)`);
    
  similarityGroups.append('circle')
    .attr('r', 10)
    .attr('class', 'similarity-badge');
    
  similarityGroups.append('text')
    .attr('class', 'similarity-text')
    .text(d => d.similarity + '%');

  // Add message button to each non-central node
  node.filter(d => d.group !== 1).each(function(d) {
    const nodeGroup = d3.select(this);
    
    // Add message button circle
    nodeGroup.append('circle')
      .attr('class', 'message-btn-bg')
      .attr('r', 8)
      .attr('cx', 15)
      .attr('cy', 8)
      .attr('fill', '#4a6fa5')
      .attr('stroke', '#ffffff')
      .attr('stroke-width', 1.5);
      
    // Add message icon
    nodeGroup.append('text')
      .attr('class', 'message-btn-icon')
      .attr('x', 15)
      .attr('y', 8)
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('fill', 'white')
      .attr('font-family', 'FontAwesome')
      .attr('font-size', '8px')
      .text('✉');
  });
  
  // Attach click handlers
  node.filter(d => d.group !== 1)
    .style('cursor', 'pointer')
    .on('click', showNodeDetails);
  
  // Add hover effect without repositioning
  node.on('mouseover', function(event, d) {
    // Use CSS class instead of transform to prevent position shift
    d3.select(this).classed('node-hover', true);
    
    // Highlight connections
    link
      .attr('stroke-opacity', l => 
        l.source.id === d.id || l.target.id === d.id ? 1 : 0.2);
      
  }).on('mouseout', function() {
    d3.select(this).classed('node-hover', false);
    link.attr('stroke-opacity', 0.7);
  });

  // Update positions on each tick of the simulation
  simulation.on('tick', () => {
    link
      .attr('x1', d => d.source.x)
      .attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x)
      .attr('y2', d => d.target.y);
    
    node.attr('transform', d => `translate(${d.x}, ${d.y})`);
  });

  // Drag functions for interactive nodes
  function dragStarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  
  function dragging(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  
  function dragEnded(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    // Fix the position where the node was dropped
    d.fx = d.x;
    d.fy = d.y;
  }
  
  // Set fixed positions for all nodes after initial layout
  simulation.on('end', function() {
    // Fix all node positions after initial layout
    data.nodes.forEach(node => {
      // Fix node positions in place to prevent drift
      node.fx = node.x;
      node.fy = node.y;
    });
  });
  
  // Set fixed position for central node immediately
  const centralNode = data.nodes.find(node => node.group === 1);
  if (centralNode) {
    centralNode.fx = width / 2;
    centralNode.fy = height / 2;
  }
  
  // Function to show detailed node information
  function showNodeDetails(event, d) {
    event.preventDefault();
    const nodeDetails = document.getElementById('nodeDetails');
    
    // Find the researcher data
    const researcherData = data.nodes.find(r => r.id === d.id);
    
    if (researcherData) {
      // Update the detail panel content
      document.getElementById('detailAvatar').src = 
        researcherData.avatar_url || 
        `https://ui-avatars.com/api/?name=${researcherData.name.replace(/ /g, '+')}&background=90cdf4&color=fff&size=150`;
      
      document.getElementById('detailName').textContent = researcherData.name;
      document.getElementById('detailSimilarityValue').textContent = researcherData.similarity;
      
      // Clear and repopulate shared interests
      const interestsContainer = document.getElementById('detailInterests');
      interestsContainer.innerHTML = '';
      
      if (d.shared_interests && d.shared_interests.length) {
        d.shared_interests.forEach(interest => {
          const tag = document.createElement('span');
          tag.className = 'interest-tag';
          tag.textContent = interest;
          interestsContainer.appendChild(tag);
        });
      } else {
        interestsContainer.textContent = 'No shared interests found';
      }
      
      // Position the details popup
      const rect = event.currentTarget.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();
      
      nodeDetails.style.left = (rect.left - containerRect.left + 40) + 'px';
      nodeDetails.style.top = (rect.top - containerRect.top - 20) + 'px';
      nodeDetails.classList.add('visible');
      
      // Close button functionality
      document.getElementById('closeNodeDetails').onclick = function() {
        nodeDetails.classList.remove('visible');
      };
      
      // Enhanced message button functionality
      const messageButton = document.getElementById('messageButton');
      
      // Check if the node represents a registered user (has a user_id)
      if (researcherData.user_id) {
        // Show the message button for registered users only
        messageButton.style.display = 'block';
        
        // Set up the message button click handler
        messageButton.onclick = function() {
          // Note: If user can see the graph, they are already logged in and premium
          // This is just a safety check in case their session expired
          const isAuthenticated = document.body.hasAttribute('data-user-authenticated');
          
          if (isAuthenticated) {
            // Open messages view in a new tab/window
            window.open(`/messaging/messages/${researcherData.user_id}`, '_blank');
          } else {
            // Show session expired tooltip
            const tooltip = bootstrap.Tooltip.getInstance(messageButton) ||
              new bootstrap.Tooltip(messageButton, {
                title: 'Your session has expired. Please log in again.',
                placement: 'top',
                trigger: 'manual'
              });
            
            tooltip.show();
            setTimeout(() => tooltip.hide(), 3000); // Hide after 3 seconds
          }
        };
      } else {
        // Hide message button for non-registered users
        messageButton.style.display = 'none';
      }
    }
  }
}

// Function to filter graph data based on limit
function filterGraphData(data, limit) {
  if (limit === 0 || !data.nodes || data.nodes.length <= 1) {
    return data;
  }
  
  // Keep the current user node and the top N similar researchers
  const currentUserNode = data.nodes.find(node => node.group === 1);
  if (!currentUserNode) return data;
  
  const researcherNodes = data.nodes
    .filter(node => node.group !== 1)
    .sort((a, b) => parseFloat(b.similarity) - parseFloat(a.similarity))
    .slice(0, limit);
  
  const filteredNodes = [currentUserNode, ...researcherNodes];
  const filteredNodeIds = filteredNodes.map(node => node.id);
  
  // Filter links to only include connections to filtered nodes
  const filteredLinks = data.links.filter(link => {
    const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
    const targetId = typeof link.target === 'object' ? link.target.id : link.target;
    return filteredNodeIds.includes(sourceId) && filteredNodeIds.includes(targetId);
  });
  
  return {
    nodes: filteredNodes,
    links: filteredLinks
  };
}
